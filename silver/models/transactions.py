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

    class State(object):
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

    @transition(field=status, source='*', target=State.Canceled)
    def cancel(self):
        """
        The transaction is canceled.
        """
        self.payment.fail()

    @transition(field=status, source=State.Uninitialized, target=State.Pending,
                conditions=[lambda t: t.payment.status == t.payment.Status.Unpaid])
    def pending(self):
        """
        Transit to the Pending state.
        """
        self.payment.process()

    @transition(field=status, source=State.Pending, target=State.Succeded)
    def succeed(self):
        """
        Finish the transaction successful.
        """
        self.payment.succeed()

    @transition(field=status, source=State.Pending, target=State.Failed)
    def fail(self):
        """
        The transaction had faild.
        """
        self.payment.fail()
