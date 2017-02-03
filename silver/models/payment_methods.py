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

from jsonfield import JSONField
from annoying.functions import get_object_or_None
from django_fsm import TransitionNotAllowed
from model_utils.managers import InheritanceManager
from cryptography.fernet import InvalidToken, Fernet

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.dispatch import receiver
from django.db.models.signals import pre_save
from django.core.exceptions import ValidationError

from silver import payment_processors

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

    def __init__(self, *args, **kwargs):
        super(PaymentMethod, self).__init__(*args, **kwargs)

        if self.id:
            try:
                payment_method_class = self.get_payment_processor().payment_method_class

                if payment_method_class:
                    self.__class__ = payment_method_class
            except AttributeError:
                pass

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

        transactions = self.transaction_set.filter(state__in=cancelable_states)

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

    def save(self, **kwargs):
        self.clean()
        super(PaymentMethod, self).save(**kwargs)

    def clean(self):
        old_instance = get_object_or_None(PaymentMethod, pk=self.pk)
        if old_instance and old_instance.canceled and not self.canceled:
            raise ValidationError("You can't reuse a canceled payment method.")

    @property
    def allowed_currencies(self):
        return self.get_payment_processor().allowed_currencies

    @property
    def public_data(self):
        return {}

    def __unicode__(self):
        return u'{} - {}'.format(self.customer,
                                 self.get_payment_processor_display())
