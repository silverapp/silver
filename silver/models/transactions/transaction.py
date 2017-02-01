# Copyright (c) 2017 Presslabs SRL
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import uuid
import logging
from decimal import Decimal

from jsonfield import JSONField
from django_fsm import post_transition
from django_fsm import FSMField, transition
from annoying.functions import get_object_or_None

from django.db import models
from django.utils import timezone
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from django.db.models.loading import get_model
from django.db.models.signals import pre_save, post_save
from django.utils.translation import ugettext_lazy as _
from django.core.validators import MinValueValidator
from silver.models.transactions.codes import (FAIL_CODES, REFUND_CODES,
                                              CANCEL_CODES)

from silver.utils.international import currencies
from silver.utils.models import AutoDateTimeField
from silver.models import BillingDocumentBase, Invoice, Proforma


logger = logging.getLogger(__name__)


class Transaction(models.Model):
    amount = models.DecimalField(
        decimal_places=2, max_digits=12,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    currency = models.CharField(
        choices=currencies, max_length=4,
        help_text='The currency used for billing.'
    )

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

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = AutoDateTimeField(default=timezone.now)

    fail_code = models.CharField(
        choices=[(code, code) for code in FAIL_CODES.keys()], max_length=32,
        null=True, blank=True
    )
    refund_code = models.CharField(
        choices=[(code, code) for code in REFUND_CODES.keys()], max_length=32,
        null=True, blank=True
    )
    cancel_code = models.CharField(
        choices=[(code, code) for code in CANCEL_CODES.keys()], max_length=32,
        null=True, blank=True
    )

    @property
    def final_fields(self):
        fields = ['proforma', 'uuid', 'payment_method', 'amount', 'currency',
                  'created_at']

        if self.invoice:
            fields.append('invoice')

        return fields

    def __init__(self, *args, **kwargs):
        self.form_class = kwargs.pop('form_class', None)

        super(Transaction, self).__init__(*args, **kwargs)

    @transition(field=state, source=States.Initial, target=States.Pending)
    def process(self):
        pass

    @transition(field=state, source=[States.Initial, States.Pending],
                target=States.Settled)
    def settle(self):
        pass

    @transition(field=state, source=[States.Initial, States.Pending],
                target=States.Canceled)
    def cancel(self, cancel_code='default', cancel_reason='Unknown cancel reason'):
        self.cancel_code = cancel_code
        logger.error(str(cancel_reason))

    @transition(field=state, source=[States.Initial, States.Pending],
                target=States.Failed)
    def fail(self, fail_code='default', fail_reason='Unknown fail reason'):
        self.fail_code = fail_code
        logger.error(str(fail_reason))

    @transition(field=state, source=States.Settled, target=States.Refunded)
    def refund(self, refund_code='default', refund_reason='Unknown refund reason'):
        self.refund_code = refund_code
        logger.error(str(refund_reason))

    def clean(self):
        document = self.document
        if not document:
            raise ValidationError(
                'The transaction must have at least one document '
                '(invoice or proforma).'
            )

        if document.state == 'draft':
            raise ValidationError(
                'The transaction must have a non-draft document '
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
        else:
            if self.invoice:
                self.proforma = self.invoice.proforma
            else:
                self.invoice = self.proforma.invoice

        if not self.pk:
            if self.currency:
                if self.currency != self.document.transaction_currency:
                    raise ValidationError(
                        "Transaction currency is different from it's document's"
                        " transaction_currency."
                    )
            else:
                self.currency = self.document.transaction_currency

            if (self.payment_method.allowed_currencies and
                    self.currency not in self.payment_method.allowed_currencies):
                raise ValidationError(
                    'Currency {} is not allowed by the payment method. '
                    'Allowed currencies are {}.'.format(
                        self.currency, self.payment_method.allowed_currencies
                    )
                )

            if self.amount:
                if self.amount != self.document.transaction_total:
                    raise ValidationError(
                        "Transaction amount is different from it's document's "
                        "transaction_total."
                    )
            else:
                self.amount = self.document.transaction_total

            if self.document.transactions.filter(
                state__in=[Transaction.States.Initial,
                           Transaction.States.Pending]
            ).exists():
                raise ValidationError(
                    'There already are active transactions for the same '
                    'billing documents.'
                )

    def full_clean(self, *args, **kwargs):
        # 'amount' and 'currency' are handled in our clean method
        kwargs['exclude'] = kwargs.get('exclude', []) + ['currency', 'amount']
        super(Transaction, self).full_clean(*args, **kwargs)

        # this assumes that nobody calls clean and then modifies this object
        # without calling clean again
        self.cleaned = True

    @property
    def can_be_consumed(self):
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
    transaction = instance

    old = get_object_or_None(Transaction, pk=transaction.pk)
    setattr(transaction, 'old_value', old)

    if old:
        for field in transaction.final_fields:
            if getattr(old, field) and getattr(transaction, field) != getattr(old, field):
                raise ValidationError("Field '%s' may not be changed." % field)

    if not getattr(transaction, 'cleaned', False):
        transaction.full_clean()

    proforma = transaction.proforma
    if proforma and proforma.invoice and not transaction.invoice:
        transaction.invoice = proforma.invoice


@receiver(post_save, sender=Transaction)
def post_transaction_save(sender, instance, **kwargs):
    if getattr(instance, 'old_value', None):
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
    # get a usable, recurring payment_method for the customer
    PaymentMethod = get_model('silver.PaymentMethod')

    payment_methods = PaymentMethod.objects.filter(
        canceled=False,
        verified=True,
        customer=document.customer
    )
    for payment_method in payment_methods:
        kwargs = {
            'invoice': isinstance(document, Invoice) and document or document.related_document,
            'proforma': isinstance(document, Proforma) and document or document.related_document,
            'payment_method': payment_method,
            'amount': document.transaction_total,
        }

        try:
            return Transaction.objects.create(**kwargs)
        except ValidationError:
            return None


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
            create_transaction_for_document(instance)
