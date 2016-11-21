from uuid import uuid4

from django.db import models
from django.utils import timezone
from django_fsm import FSMField, transition


class Transaction(models.Model):
    payment_method = models.ForeignKey('PaymentMethod')
    payment = models.ForeignKey('Payment')
    uuid = models.UUIDField(default=uuid4)
    valid_until = models.DateTimeField(null=True, blank=True)
    last_access = models.DateTimeField(null=True, blank=True)
    disabled = models.BooleanField(default=False)

    status = FSMField(default='uninitialized')

    class States(object):
        Uninitialized = 'uninitialized'
        Pending = 'pending'
        Succeded = 'succeded'
        Failed = 'failed'
        Canceled = 'canceled'

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

    @transition(field=status, source='*', target=States.Canceled)
    def cancel(self):
        """
        The transaction is canceled.
        """
        pass

    @transition(field=status, source=States.Uninitialized, target=States.Pending,
                conditions=[lambda t: t.payment.status == t.payment.Status.Unpaid])
    def process(self):
        """
        Transit to the Pending state.
        """

    @transition(field=status, source=States.Pending, target=States.Succeded)
    def succeed(self):
        """
        Finish the transaction successful.
        """
        pass

    @transition(field=status, source=States.Pending, target=States.Failed)
    def fail(self):
        """
        The transaction had faild.
        """
        pass
