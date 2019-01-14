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

from __future__ import absolute_import, unicode_literals

import uuid
import logging

from decimal import Decimal

from annoying.fields import JSONField
from annoying.functions import get_object_or_None
from django_fsm import FSMField, post_transition, transition

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible, force_text
from django.utils.translation import ugettext_lazy as _

from silver.models import Invoice, Proforma
from silver.models.transactions.codes import FAIL_CODES, REFUND_CODES, CANCEL_CODES
from silver.utils.international import currencies
from silver.utils.models import AutoDateTimeField, AutoCleanModelMixin

logger = logging.getLogger(__name__)


@python_2_unicode_compatible
class Transaction(AutoCleanModelMixin,
                  models.Model):
    _provider = None

    amount = models.DecimalField(
        decimal_places=2, max_digits=12,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    currency = models.CharField(
        choices=currencies, max_length=4,
        help_text='The currency used for billing.'
    )

    class Meta:
        ordering = ['-id']

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

    proforma = models.ForeignKey("BillingDocumentBase", null=True, blank=True,
                                 on_delete=models.SET_NULL, related_name='proforma_transactions')
    invoice = models.ForeignKey("BillingDocumentBase", null=True, blank=True,
                                on_delete=models.SET_NULL, related_name='invoice_transactions')

    payment_method = models.ForeignKey('PaymentMethod', on_delete=models.PROTECT)
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
        fields = ['proforma', 'invoice', 'uuid', 'payment_method', 'amount',
                  'currency', 'created_at']

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

    @transaction.atomic()
    def save(self, *args, **kwargs):
        if not self.pk:
            # Creating a new Transaction so we lock the DB rows for related billing documents and
            # transactions
            if self.proforma:
                Proforma.objects.select_for_update().filter(pk=self.proforma.pk)
            elif self.invoice:
                Invoice.objects.select_for_update().filter(pk=self.invoice.pk)

            Transaction.objects.select_for_update().filter(Q(proforma=self.proforma) |
                                                           Q(invoice=self.invoice))

        super(Transaction, self).save(*args, **kwargs)

    def clean(self):
        # Validate documents
        document = self.document
        if not document:
            raise ValidationError(
                'The transaction must have at least one billing document '
                '(invoice or proforma).'
            )

        if document.state == document.STATES.DRAFT:
            raise ValidationError(
                'The transaction must have a non-draft billing document '
                '(invoice or proforma).'
            )

        if self.invoice and self.proforma:
            if self.invoice.related_document != self.proforma:
                raise ValidationError('Invoice and proforma are not related.')
        else:
            if self.invoice:
                self.proforma = self.invoice.related_document
            else:
                self.invoice = self.proforma.related_document

        if document.customer != self.customer:
            raise ValidationError(
                'Customer doesn\'t match with the one in documents.'
            )

        # New transaction
        if not self.pk:
            if document.state != document.STATES.ISSUED:
                raise ValidationError(
                    'Transactions can only be created for issued documents.'
                )

            if self.currency:
                if self.currency != self.document.transaction_currency:
                    message = "Transaction currency is different from it's document's "\
                              "transaction_currency."
                    raise ValidationError(message)
            else:
                self.currency = self.document.transaction_currency

            if (self.payment_method.allowed_currencies and
                    self.currency not in self.payment_method.allowed_currencies):
                message = 'Currency {} is not allowed by the payment method. Allowed currencies ' \
                          'are {}.'.format(
                              self.currency, self.payment_method.allowed_currencies
                          )
                raise ValidationError(message)
            if self.amount:
                if self.amount > self.document.amount_to_be_charged_in_transaction_currency:
                    message = "Amount is greater than the amount that should be charged in order " \
                              "to pay the billing document."
                    raise ValidationError(message)
            else:
                self.amount = self.document.amount_to_be_charged_in_transaction_currency
        else:
            # clean final fields
            errors = {}
            for field in self.final_fields:
                old_value = self.initial_state.get(field)
                current_value = self.current_state.get(field)

                if old_value is not None and old_value != current_value:
                    errors[field] = 'This field may not be modified.'
            if errors:
                raise ValidationError(errors)

    def full_clean(self, *args, **kwargs):
        # 'amount' and 'currency' are handled in our clean method
        kwargs['exclude'] = kwargs.get('exclude', []) + ['currency', 'amount']

        super(Transaction, self).full_clean(*args, **kwargs)

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

    @document.setter
    def document(self, value):
        if isinstance(value, Invoice):
            self.invoice = value
        elif isinstance(value, Proforma):
            self.proforma = value
        else:
            raise ValueError(
                'The provided document is not an invoice or a proforma.'
            )

    @property
    def provider(self):
        return self._provider or self.document.provider

    @provider.setter
    def provider(self, provider):
        self._provider = provider

    @property
    def payment_processor(self):
        return self.payment_method.payment_processor

    def update_document_state(self):
        if (
            self.state == Transaction.States.Settled and
            not self.document.amount_to_be_charged_in_transaction_currency and
            self.document.state != self.document.STATES.PAID
        ):
            self.document.pay()

    def __str__(self):
        return force_text(self.uuid)


@receiver(post_transition)
def post_transition_callback(sender, instance, name, source, target, **kwargs):
    if issubclass(sender, Transaction):
        setattr(instance, '.recently_transitioned', target)


@receiver(post_save, sender=Transaction)
def post_transaction_save(sender, instance, **kwargs):
    transaction = instance

    if hasattr(transaction, '.recently_transitioned'):
        delattr(transaction, '.recently_transitioned')
        transaction.update_document_state()

    if hasattr(transaction, '.cleaned'):
        delattr(transaction, '.cleaned')

    if not getattr(transaction, 'previous_instance', None):
        # we know this instance is freshly made as it doesn't have an old_value
        logger.info('[Models][Transaction]: %s', {
            'detail': 'A transaction was created.',
            'transaction_id': transaction.id,
            'customer_id': transaction.customer.id,
            'invoice_id': transaction.invoice.id if transaction.invoice else None,
            'proforma_id':
                transaction.proforma.id if transaction.proforma else None
        })
