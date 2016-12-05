from django_fsm import FSMField, transition
from jsonfield import JSONField
from model_utils.managers import InheritanceManager

from django.db import models
from django.utils import timezone

from billing_entities import Customer
from payment_processors import PaymentProcessorManager
from payment_processors.fields import PaymentProcessorField


class PaymentMethodInvalid(Exception):
    pass


class PaymentMethod(models.Model):
    payment_processor = PaymentProcessorField(
        choices=PaymentProcessorManager.get_choices(),
        blank=False
    )
    customer = models.ForeignKey(Customer)
    added_at = models.DateTimeField(default=timezone.now)
    verified_at = models.DateTimeField(null=True, blank=True)
    data = JSONField(blank=True, null=True)

    objects = InheritanceManager()

    class States(object):
        Uninitialized = 'uninitialized'
        Unverified = 'unverified'
        Enabled = 'enabled'
        Disabled = 'disabled'
        Removed = 'removed'

        Choices = (
            (Uninitialized, 'Uninitialized'),
            (Unverified, 'Unverified'),
            (Enabled, 'Enabled'),
            (Disabled, 'Disabled'),
            (Removed, 'Removed')
        )

        @classmethod
        def as_list(cls):
            return [choice[0] for choice in cls.Choices]

        @classmethod
        def allowed_initial_states(cls):
            return [cls.Uninitialized, cls.Unverified, cls.Enabled]

        @classmethod
        def invalid_initial_states(cls):
            return list(set(cls.as_list()) - set(cls.allowed_initial_states()))

    state = FSMField(choices=States.Choices, default=States.Uninitialized)
    state_transitions = {
        'initialize_unverified': {
            'source': States.Uninitialized,
            'target': States.Unverified
        },
        'initialize_enabled': {
            'source': States.Uninitialized,
            'target': States.Enabled
        },
        'verify': {
            'source': States.Unverified,
            'target': States.Enabled
        },
        'remove': {
            'source': [States.Enabled, States.Disabled, States.Unverified],
            'target': States.Removed
        },
        'disable': {
            'source': States.Enabled,
            'target': States.Disabled
        },
        'reenable': {
            'source': States.Disabled,
            'target': States.Enabled
        }
    }

    def __init__(self, *args, **kwargs):
        super(PaymentMethod, self).__init__(*args, **kwargs)

        if self.id:
            try:
                payment_method_class = self.payment_processor.payment_method_class

                if payment_method_class:
                    self.__class__ = payment_method_class
            except AttributeError:
                pass

    @transition(field='state',
                **state_transitions['initialize_unverified'])
    def initialize_unverified(self, initial_data=None):
        pass

    @transition(field='state',
                **state_transitions['initialize_enabled'])
    def initialize_enabled(self, initial_data=None):
        pass

    @transition(field='state',
                **state_transitions['verify'])
    def verify(self):
        pass

    @transition(field='state',
                **state_transitions['remove'])
    def remove(self):
        """
        Methods that implement this, need to remove the payment method from
        the real Payment Processor or raise TransitionNotAllowed
        """
        pass

    @transition(field='state',
                **state_transitions['disable'])
    def disable(self):
        pass

    @transition(field='state',
                **state_transitions['reenable'])
    def reenable(self):
        pass

    def delete(self, using=None):
        if not self.state == self.States.Uninitialized:
            self.remove()

        super(PaymentMethod, self).delete(using=using)

    def pay_billing_document(self, document):
        if self.state == self.States.Enabled:
            self.payment_processor.pay_billing_document(document, self)
        else:
            raise PaymentMethodInvalid

    def __unicode__(self):
        return u'{} - {}'.format(self.customer, self.payment_processor)
