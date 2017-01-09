import logging
import uuid
from decimal import Decimal

from annoying.functions import get_object_or_None

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, URLValidator
from django.db import models
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django_fsm import FSMField, transition, TransitionNotAllowed
from django_fsm import post_transition
from jsonfield import JSONField


from silver.models import BillingDocumentBase, Invoice, PaymentMethod, Proforma
from silver.utils.international import currencies


logger = logging.getLogger(__name__)


class Transaction(models.Model):
    amount = models.DecimalField(
        decimal_places=2, max_digits=8,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    currency = models.CharField(
        choices=currencies, max_length=4, default='USD',
        help_text='The currency used for billing.'
    )
    currency_rate_date = models.DateField(blank=True, null=True)

    class States:
        Initial = 'initial'
        Pending = 'pending'
        Settled = 'settled'
        Failed = 'failed'
        Canceled = 'canceled'
        Refunded = 'refunded'

        @classmethod
        def as_list(cls):
            return [getattr(cls, state) for state in vars(cls).keys() if
                    state[0].isupper()]

        @classmethod
        def as_choices(cls):
            return (
                (state, _(state.capitalize())) for state in cls.as_list()
            )

    external_reference = models.CharField(max_length=256, null=True, blank=True)
    data = JSONField(default={}, null=True, blank=True)
    state = FSMField(max_length=8, choices=States.as_choices(),
                     default=States.Initial)

    proforma = models.ForeignKey("Proforma", null=True, blank=True)
    invoice = models.ForeignKey("Invoice", null=True, blank=True)
    payment_method = models.ForeignKey('PaymentMethod')
    uuid = models.UUIDField(default=uuid.uuid4)
    valid_until = models.DateTimeField(null=True, blank=True)
    last_access = models.DateTimeField(null=True, blank=True)
    consumable = models.BooleanField(default=True)

    success_url = models.TextField(null=True, blank=True,
                                   validators=[URLValidator()])
    failed_url = models.TextField(null=True, blank=True,
                                  validators=[URLValidator()])

    def __init__(self, *args, **kwargs):
        self.form_class = kwargs.pop('form_class', None)

        super(Transaction, self).__init__(*args, **kwargs)

    @transition(field=state, source=States.Initial, target=States.Pending)
    def process(self):
        pass

    @transition(field=state, source=States.Pending, target=States.Settled)
    def settle(self):
        pass

    @transition(field=state, source=[States.Initial, States.Pending],
                target=States.Canceled)
    def cancel(self):
        pass

    @transition(field=state, source=States.Pending, target=States.Failed)
    def fail(self):
        pass

    @transition(field=state, source=States.Settled, target=States.Refunded)
    def refund(self):
        pass

    def clean(self):
        document = self.document
        if not document:
            raise ValidationError(
                'The transaction must have at least one document '
                '(invoice or proforma).'
            )

        if document.provider != self.provider:
            raise ValidationError(
                'Provider doesn\'t match with the one in documents.'
            )

        if document.customer != self.customer:
            raise ValidationError(
                'Customer doesn\'t match with the one in documents.'
            )

        if self.invoice and self.proforma:
            if self.invoice.proforma != self.proforma:
                raise ValidationError('Invoice and proforma are not related.')

    @property
    def can_be_consumed(self):
        if not self.consumable:
            return False

        if self.valid_until and self.valid_until < timezone.now():
            return False

        if self.state != Transaction.States.Initial:
            return False

        return True

    @property
    def customer(self):
        return self.payment_method.customer

    @property
    def document(self):
        return self.invoice or self.proforma

    @property
    def provider(self):
        return self.document.provider

    @property
    def payment_processor(self):
        return self.payment_method.payment_processor

    def __unicode__(self):
        return unicode(self.uuid)


@receiver(pre_save, sender=Transaction)
def pre_transaction_save(sender, instance=None, **kwargs):
    old = get_object_or_None(Transaction, pk=instance.pk)
    setattr(instance, 'old_value', old)


@receiver(post_save, sender=Transaction)
def post_transaction_save(sender, instance, **kwargs):
    if instance.old_value:
        return

    # we know this instance is freshly made as it doesn't have an old_value
    logger.info('[Models][Transaction]: %s', {
        'detail': 'A transaction was created.',
        'transaction_id': instance.id,
        'customer_id': instance.customer.id,
        'invoice_id': instance.invoice.id if instance.invoice else None,
        'proforma_id':
            instance.proforma.id if instance.proforma else None
    })


def _sync_transaction_state_with_document(transaction, target):
    if target == Transaction.States.Settled:
        if transaction.document and \
                transaction.document.state != transaction.document.STATES.PAID:
            transaction.document.pay()
            transaction.document.save()


def create_transaction_for_document(document):
    if not document.transactions.filter(
        state__in=[Transaction.States.Initial, Transaction.States.Pending]
    ):
        # get a usable, recurring payment_method for the customer
        payment_methods = PaymentMethod.objects.filter(
            enabled=True,
            verified=True,
            customer=document.customer
        )
        for payment_method in payment_methods:
            if (payment_method.verified and
                    payment_method.enabled):
                # create transaction
                kwargs = {
                    'invoice': document if isinstance(document, Invoice) else
                               document.related_document,
                    'proforma': document if isinstance(document, Proforma) else
                                document.related_document,
                    'payment_method': payment_method,
                    'amount': document.total
                }

                return Transaction.objects.create(**kwargs)


@receiver(post_transition)
def post_transition_callback(sender, instance, name, source, target, **kwargs):
    """
    Syncs the state of the related documents of the transaction with the
    transaction state
    """

    if issubclass(sender, Transaction):
        _sync_transaction_state_with_document(instance, target)

    elif issubclass(sender, BillingDocumentBase):
        if target == BillingDocumentBase.STATES.ISSUED:
            transaction = create_transaction_for_document(instance)

            if transaction:
                transaction.payment_processor.execute_transaction(transaction)
