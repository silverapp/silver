from braintree.exceptions import (
    AuthenticationError, AuthorizationError, DownForMaintenanceError,
    ServerError, UpgradeRequiredError, NotFoundError
)
from silver.models import PaymentMethod


class BraintreePaymentMethod(PaymentMethod):
    class Meta:
        proxy = True

    @property
    def sdk(self):
        return self.payment_processor.sdk

    @property
    def braintree_transaction(self):
        try:
            return self.sdk.Transaction.find(self.braintree_id)
        except NotFoundError:
            return None

    @property
    def braintree_id(self):
        return self.data.get('braintree_id')

    @property
    def client_token(self):
        try:
            return self.sdk.ClientToken.generate({
                'customer_id': self.braintree_id
            })
        except (AuthenticationError, AuthorizationError, DownForMaintenanceError,
                ServerError, UpgradeRequiredError):
            return None

    def pay_billing_document(self, billing_document):
        raise NotImplementedError
