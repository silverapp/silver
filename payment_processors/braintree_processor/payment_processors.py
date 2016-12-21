import braintree
from braintree.exceptions import (AuthenticationError, AuthorizationError,
                                  DownForMaintenanceError, ServerError,
                                  UpgradeRequiredError)

from .payment_methods import BraintreePaymentMethod
from .views import BraintreeTransactionView
from silver.models.payment_processors.base import PaymentProcessorBase
from silver.models.payment_processors.mixins import TriggeredProcessorMixin


class BraintreeTriggered(PaymentProcessorBase, TriggeredProcessorMixin):
    view_class = BraintreeTransactionView
    payment_method_class = BraintreePaymentMethod

    def setup(self, data):
        environment = data.pop('environment', None)
        braintree.Configuration.configure(environment, **data)

    @property
    def client_token(self):
        try:
            return braintree.ClientToken.generate()
        except (AuthenticationError, AuthorizationError, DownForMaintenanceError,
                ServerError, UpgradeRequiredError):
            return None

    def refund_transaction(self, transaction, payment_method=None):
        pass

    def void_transaction(self, transaction, payment_method=None):
        pass

    def manage_transaction(self, transaction):
        result = braintree.Transaction.sale({
            'amount': transaction.amount,
            'payment_method_nonce': ''
        })
