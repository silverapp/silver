import uuid
from decimal import Decimal

import logging

from annoying.functions import get_object_or_None
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django_fsm import FSMField, TransitionNotAllowed
from django_fsm import post_transition
from silver.mail import (send_new_transaction_email,
                         send_pending_transaction_email,
                         send_failed_transaction_email,
                         send_refunded_transaction_email,
                         send_settled_transaction_email)


logger = logging.getLogger(__name__)


class Transaction(models.Model):
    amount = models.DecimalField(
        decimal_places=2, max_digits=8,
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    class States(object):
        Initial = 'initial'
        Pending = 'pending'
        Settled = 'settled'
        Failed = 'failed'
        Canceled = 'canceled'
        Refunded = 'refunded'

    STATE_CHOICES = (
        (States.Initial, _('Initial')),
        (States.Pending, _('Pending')),
        (States.Settled, _('Settled')),
        (States.Canceled, _('Canceled')),
        (States.Failed, _('Failed')),
        (States.Refunded, _('Refunded')),
    )
    state = FSMField(max_length=8, choices=STATE_CHOICES,
                     default=States.Initial)
    proforma = models.OneToOneField("Proforma", null=True, blank=True)
    invoice = models.OneToOneField("Invoice", null=True, blank=True)
    payment_method = models.ForeignKey('PaymentMethod')
    uuid = models.UUIDField(default=uuid.uuid4)
    valid_until = models.DateTimeField(null=True, blank=True)
    last_access = models.DateTimeField(null=True, blank=True)
    disabled = models.BooleanField(default=False)

    def __init__(self, *args, **kwargs):
        self.form_class = kwargs.pop('form_class', None)

        super(Transaction, self).__init__(*args, **kwargs)

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
    def is_consumable(self):
        if self.disabled:
            return False

        if self.valid_until and self.valid_until > timezone.now():
            return False

        if self.state is not Transaction.States.Initial:
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


def send_email_with_current_state(transaction):
    if transaction.state is Transaction.States.Initial:
        send_new_transaction_email(transaction)
    elif transaction.state is Transaction.States.Pending:
        send_pending_transaction_email(transaction)
    elif transaction.state is Transaction.States.Failed:
        send_failed_transaction_email(transaction)
    elif transaction.state is Transaction.States.Settled:
        send_settled_transaction_email(transaction)
    elif transaction.state is Transaction.States.Refunded:
        send_refunded_transaction_email(transaction)


@receiver(pre_save, sender=Transaction)
def pre_transaction_save(sender, instance=None, **kwargs):
    old = get_object_or_None(Transaction, pk=instance.pk)
    setattr(instance, 'old_value', old)


@receiver(post_save, sender=Transaction)
def post_transaction_save(sender, instance, **kwargs):
    if not instance.old_value:
        logger.info('[Models][Transaction]: %s', {
            'detail': 'A transaction was created.',
            'transaction_id': instance.id,
            'customer_id': instance.customer.id,
            'invoice_id': instance.invoice.id if instance.invoice else None,
            'proforma_id':
                instance.proforma.id if instance.proforma else None
        })

        send_new_transaction_email(instance)

        if instance.state is not Transaction.States.Initial:
            # The transaction was created with a state other than the initial
            # one
            send_email_with_current_state(instance)


@receiver(post_transition)
def post_transition_callback(sender, instance, name, source, target, **kwargs):
    """
    Syncs the state of the related documents of the transaction with the
    transaction state
    """
    if issubclass(sender, Transaction):
        if target == Transaction.States.Settled:
            send_mail = False

            if instance.proforma and \
                    instance.proforma.state != instance.proforma.STATES.PAID:
                try:
                    instance.proforma.pay()
                    instance.proforma.save()

                    send_mail = True
                except TransitionNotAllowed:
                    logger.warning('[Models][Transaction]: %s', {
                        'detail': 'Couldn\'t automatically pay proforma.',
                        'transaction_id': instance.id,
                        'transaction_state': instance.state,
                        'proforma_id': instance.proforma.id,
                        'proforma_state': instance.proforma.state
                    })

            if instance.invoice and \
                    instance.invoice.state != instance.invoice.STATES.PAID:
                try:
                    instance.invoice.pay()
                    instance.invoice.save()

                    send_mail = True
                except TransitionNotAllowed:
                    logger.warning('[Models][Transaction]: %s', {
                        'detail': 'Couldn\'t automatically pay invoice.',
                        'transaction_id': instance.id,
                        'transaction_state': instance.state,
                        'invoice_id': instance.invoice.id,
                        'invoice_state': instance.invoice.state
                    })

            if send_mail:
                send_email_with_current_state(instance)
