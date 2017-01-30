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
from cryptography.fernet import InvalidToken, Fernet
from model_utils.managers import InheritanceManager

from django.db import models
from django.conf import settings
from django.utils import timezone

from .billing_entities import Customer

from silver import payment_processors


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
    enabled = models.BooleanField(default=True)

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

    @property
    def allowed_currencies(self):
        return self.get_payment_processor().allowed_currencies

    @property
    def public_data(self):
        return {}

    def __unicode__(self):
        return u'{} - {}'.format(self.customer,
                                 self.get_payment_processor_display())
