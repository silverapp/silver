import logging


logger = logging.getLogger(__name__)


class PaymentProcessorMeta(type):
    def __repr__(self):
        return self.name

    def __unicode__(self):
        return unicode(self.name)

    def __str__(self):
        return str(self.name)


class PaymentProcessorTypes(object):
    Manual = "manual"
    Automatic = "automatic"
    Triggered = "triggered"
    Mixed = "mixed"


class ManualProcessorMixin(object):
    type = PaymentProcessorTypes.Manual


class BaseActionableProcessor(object):
    """
        Not a Manual type Processor
    """

    @staticmethod
    def refund_payment(payment, payment_method=None):
        """
            Refunds / returns the money to the customer
        """

        raise NotImplementedError

    @staticmethod
    def void_payment(payment, payment_method=None):
        """
            Voids / interrupts an ongoing payment
        """

        raise NotImplementedError

    @staticmethod
    def manage_payment(payment):
        """
            Only gets called for unpaid or pending payments that point to this
            specific Processor
        """

        raise NotImplementedError


class AutomaticProcessorMixin(BaseActionableProcessor):
    type = PaymentProcessorTypes.Automatic

    @staticmethod
    def setup_automated_payments(customer):
        """
            Does the necessary operations to ensure payments are automatically
            processed by the processor service.
        """
        raise NotImplementedError


class TriggeredProcessorMixin(BaseActionableProcessor):
    type = PaymentProcessorTypes.Triggered

    @staticmethod
    def charge_payment(payment, payment_method):
        """
            Used to convert a Payment to a specific Payment type for a specific
            Processor
        """

        raise NotImplementedError


class MixedProcessorMixin(AutomaticProcessorMixin, TriggeredProcessorMixin):
    type = PaymentProcessorTypes.Mixed


class GenericPaymentProcessor(object):
    __metaclass__ = PaymentProcessorMeta

    name = None
    payment_method_class = None
    transaction_class = None

    @staticmethod
    def setup(data):
        """
            Sets up the Payment Processor
        """

        raise NotImplementedError

    def __unicode__(self):
        return unicode(self.name)
