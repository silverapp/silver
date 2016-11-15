import uuid

from django.db import models
from django.utils import timezone


class Transaction(models.Model):
    payment_method = models.ForeignKey('PaymentMethod')
    payment = models.ForeignKey('Payment')
    uuid = models.UUIDField(default=uuid.uuid4)
    valid_until = models.DateTimeField(null=True, blank=True)
    last_access = models.DateTimeField(null=True, blank=True)
    disabled = models.BooleanField(default=False)

    def __init__(self, *args, **kwargs):
        self.form_class = kwargs.pop('form_class', None)

        super(Transaction, self).__init__(*args, **kwargs)

    @property
    def is_usable(self):
        return not self.disabled and (not self.valid_until or
                                      self.valid_until > timezone.now())

    @property
    def customer(self):
        return self.payment_method.customer

    @property
    def payment_processor(self):
        return self.payment_method.payment_processor
