from jsonfield import JSONField
from django_fsm import FSMField, transition
from cryptography.fernet import InvalidToken, Fernet
from model_utils.managers import InheritanceManager

from django.db import models
from django.conf import settings
from django.utils import timezone

from silver.models.payment_processors.fields import PaymentProcessorField

from .billing_entities import Customer


class PaymentMethodInvalid(Exception):
    pass


class PaymentMethod(models.Model):
    payment_processor = PaymentProcessorField(
        blank=False, null=False, max_length=256
    )
    customer = models.ForeignKey(Customer)
    added_at = models.DateTimeField(default=timezone.now)
    data = JSONField(blank=True, null=True, default={})

    verified = models.BooleanField(default=False)
    enabled = models.BooleanField(default=True)

    objects = InheritanceManager()

    customer = models.ForeignKey(Customer)
    added_at = models.DateTimeField(default=timezone.now)
    data = JSONField(blank=True, null=True, default={})

    objects = InheritanceManager()

    def __init__(self, *args, **kwargs):
        super(PaymentMethod, self).__init__(*args, **kwargs)

        if self.id:
            try:
                payment_method_class = self.payment_processor.payment_method_class

                if payment_method_class:
                    self.__class__ = payment_method_class
            except AttributeError:
                pass

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
    def public_data(self):
        return {}

    def __unicode__(self):
        return u'{} - {}'.format(self.customer, self.payment_processor)
