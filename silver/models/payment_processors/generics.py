import logging

from django.http import HttpResponse
from django.utils.deconstruct import deconstructible
from django.views.decorators.csrf import csrf_protect
from silver.models.payment_processors.forms import GenericPaymentForm

logger = logging.getLogger(__name__)


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

    def refund_payment(self, payment, payment_method=None):
        """
            Refunds / returns the money to the customer
        """

        raise NotImplementedError

    def void_payment(self, payment, payment_method=None):
        """
            Voids / interrupts an ongoing payment
        """

        raise NotImplementedError

    def manage_payment(self, payment):
        """
            Only gets called for unpaid or pending payments that point to this
            specific Processor
        """

        raise NotImplementedError


class AutomaticProcessorMixin(BaseActionableProcessor):
    type = PaymentProcessorTypes.Automatic

    def setup_automated_payments(self, customer):
        """
            Does the necessary operations to ensure payments are automatically
            processed by the processor service.
        """
        raise NotImplementedError


class TriggeredProcessorMixin(BaseActionableProcessor):
    type = PaymentProcessorTypes.Triggered

    def charge_payment(self, payment, payment_method):
        """
            Used to convert a Payment to a specific Payment type for a specific
            Processor
        """

        raise NotImplementedError


class MixedProcessorMixin(AutomaticProcessorMixin, TriggeredProcessorMixin):
    type = PaymentProcessorTypes.Mixed


@deconstructible
class GenericPaymentProcessor(object):
    name = None
    payment_method_class = None
    transaction_class = None
    form_class = GenericPaymentForm

    def setup(self, data):
        """
            Sets up the Payment Processor
        """

        raise NotImplementedError

    def render_form(self, request, transaction):
        return self.form_class(payment_method=transaction.payment_method,
                               payment=transaction.payment).render()

    def handle_customer_request(self, request, transaction):
        if self.form_class:
            return HttpResponse(self.render_form(request, transaction))
        else:
            raise NotImplementedError

    def __repr__(self):
        return self.name

    def __unicode__(self):
        return unicode(self.name)

    def __str__(self):
        return str(self.name)

    def __eq__(self, other):
        return self.__class__ is other.__class__
