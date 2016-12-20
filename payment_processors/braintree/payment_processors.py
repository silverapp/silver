import braintree
from braintree.exceptions import (AuthenticationError, AuthorizationError,
                                  DownForMaintenanceError, ServerError,
                                  UpgradeRequiredError)
from .views import BraintreeTransactionView
from silver.models.transactions import Transaction

from silver.models.payment_processors.generics import (GenericPaymentProcessor,
                                                       TriggeredProcessorMixin)


class BraintreeTriggered(GenericPaymentProcessor, TriggeredProcessorMixin):
    name = 'BraintreeTriggered'
    transaction_class = Transaction
    view_class = BraintreeTransactionView

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
