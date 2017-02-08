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
from itertools import chain

from annoying.functions import get_object_or_None
from cryptography.fernet import InvalidToken, Fernet
from django_fsm import TransitionNotAllowed
from jsonfield import JSONField
from model_utils.managers import InheritanceManager

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from silver import payment_processors
from silver.models import Invoice, Proforma

from .billing_entities import Customer
from .transactions import Transaction


class PaymentMethodInvalid(Exception):
    pass


class PaymentMethod(models.Model):
    class PaymentProcessors:
        @classmethod
        def as_choices(cls):
            for name in settings.PAYMENT_PROCESSORS.keys():
                yield (name, name)

        @classmethod
        def as_list(cls):
            return [name for name in settings.PAYMENT_PROCESSORS.keys()]

    payment_processor = models.CharField(choices=PaymentProcessors.as_choices(),
                                         blank=False, null=False, max_length=256)
    customer = models.ForeignKey(Customer)
    added_at = models.DateTimeField(default=timezone.now)
    data = JSONField(blank=True, null=True, default={})

    verified = models.BooleanField(default=False)
    canceled = models.BooleanField(default=False)

    valid_until = models.DateTimeField(null=True, blank=True)
    display_info = models.CharField(max_length=256, null=True, blank=True)

    objects = InheritanceManager()

    @property
    def final_fields(self):
        return ['payment_processor', 'customer', 'added_at']

    @property
    def irreversible_fields(self):
        return ['verified', 'canceled']

    def __init__(self, *args, **kwargs):
        super(PaymentMethod, self).__init__(*args, **kwargs)

        if self.id:
            try:
                payment_method_class = self.get_payment_processor().payment_method_class

                if payment_method_class:
                    self.__class__ = payment_method_class
            except AttributeError:
                pass

    @property
    def transactions(self):
        return self.transaction_set.all()

    def get_payment_processor(self):
        return payment_processors.get_instance(self.payment_processor)

    def delete(self, using=None):
        if not self.state == self.States.Uninitialized:
            self.remove()

        super(PaymentMethod, self).delete(using=using)

    def encrypt_data(self, data):
        key = settings.PAYMENT_METHOD_SECRET
        return Fernet(key).encrypt(bytes(data))

    def decrypt_data(self, crypted_data):
        key = settings.PAYMENT_METHOD_SECRET

        try:
            return str(Fernet(key).decrypt(bytes(crypted_data)))
        except InvalidToken:
            return None

    def cancel(self):
        if self.canceled:
            raise ValidationError("You can't cancel a canceled payment method.")

        cancelable_states = [Transaction.States.Initial,
                             Transaction.States.Pending]

        transactions = self.transactions.filter(state__in=cancelable_states)

        errors = []
        for transaction in transactions:
            if transaction.state == Transaction.States.Initial:
                try:
                    transaction.cancel()
                except TransitionNotAllowed:
                    errors.append("Transaction {} couldn't be canceled".format(transaction.uuid))

            if transaction.state == Transaction.States.Pending:
                payment_processor = self.get_payment_processor()
                if (hasattr(payment_processor, 'void_transaction') and
                        not payment_processor.void_transaction(transaction)):
                    errors.append("Transaction {} couldn't be voided".format(transaction.uuid))

            transaction.save()

        if errors:
            return errors

        self.canceled = True
        self.save()

        return None

    def clean_with_previous_instance(self, previous_instance):
        if not previous_instance:
            return

        for field in self.final_fields:
            old_value = getattr(previous_instance, field, None)
            current_value = getattr(self, field, None)

            if old_value != current_value:
                raise ValidationError(
                    "Field '%s' may not be changed." % field
                )

        for field in self.irreversible_fields:
            old_value = getattr(previous_instance, field, None)
            current_value = getattr(self, field, None)

            if old_value and old_value != current_value:
                raise ValidationError(
                    "Field '%s' may not be changed anymore." % field
                )

    def full_clean(self, *args, **kwargs):
        previous_instance = kwargs.pop('previous_instance', None)

        super(PaymentMethod, self).full_clean(*args, **kwargs)

        self.clean_with_previous_instance(previous_instance)

        # this assumes that nobody calls clean and then modifies this object
        # without calling clean again
        setattr(self, '.cleaned', True)

    @property
    def allowed_currencies(self):
        return self.get_payment_processor().allowed_currencies

    @property
    def public_data(self):
        return {}

    def __unicode__(self):
        return u'{} - {}'.format(self.customer,
                                 self.get_payment_processor_display())


def create_transactions_for_issued_documents(payment_method):
    customer = payment_method.customer

    if payment_method.canceled or not payment_method.verified:
        return []

    transactions = []

    for document in chain(
        Proforma.objects.filter(invoice=None, customer=customer,
                                state=Proforma.STATES.ISSUED),
        Invoice.objects.filter(state=Invoice.STATES.ISSUED, customer=customer)
    ):
        try:
            transactions.append(Transaction.objects.create(
                document=document, payment_method=payment_method
            ))
        except ValidationError:
            continue

    return transactions


@receiver(pre_save)
def pre_payment_method_save(sender, instance=None, **kwargs):
    if not isinstance(instance, PaymentMethod):
        return

    payment_method = instance

    previous_instance = get_object_or_None(PaymentMethod, pk=payment_method.pk)
    setattr(payment_method, '.previous_instance', previous_instance)

    if not getattr(payment_method, '.cleaned', False):
        payment_method.full_clean(previous_instance=previous_instance)


@receiver(post_save)
def post_payment_method_save(sender, instance, **kwargs):
    if not isinstance(instance, PaymentMethod):
        return

    payment_method = instance

    if hasattr(payment_method, '.cleaned'):
        delattr(payment_method, '.cleaned')

    previous_instance = getattr(payment_method, '.previous_instance', None)

    if not (settings.SILVER_AUTOMATICALLY_CREATE_TRANSACTIONS or
            not payment_method.verified or
            (not payment_method.get_payment_processor().type ==
                payment_processors.Types.Triggered)):
        return

    if not previous_instance or not previous_instance.verified:
        create_transactions_for_issued_documents(payment_method)
