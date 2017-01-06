import braintree as sdk
from braintree.exceptions import (
    AuthenticationError, AuthorizationError, DownForMaintenanceError,
    ServerError, UpgradeRequiredError, NotFoundError
)

from django_fsm import transition

from silver.models import PaymentMethod


class BraintreePaymentMethod(PaymentMethod):
    class Meta:
        proxy = True

    class Types:
        PayPal = 'paypal_account'
        CreditCard = 'credit_card'

    @property
    def braintree_transaction(self):
        try:
            return sdk.Transaction.find(self.braintree_id)
        except NotFoundError:
            return None

    @property
    def braintree_id(self):
        return self.data.get('braintree_id')

    @property
    def client_token(self):
        try:
            return sdk.ClientToken.generate({
                'customer_id': self.braintree_id
            })
        except (AuthenticationError, AuthorizationError, DownForMaintenanceError,
                ServerError, UpgradeRequiredError):
            return None

    @property
    def token(self):
        return self.decrypt_data(self.data.get('token'))

    @token.setter
    def token(self, value):
        self.data['token'] = self.encrypt_data(value)

    @property
    def nonce(self):
        return self.decrypt_data(self.data.get('nonce'))

    @nonce.setter
    def nonce(self, value):
        self.data['nonce'] = self.encrypt_data(value)

    @property
    def is_recurring(self):
        return self.data.get('is_recurring', False)

    @is_recurring.setter
    def is_recurring(self, value):
        self.data['is_recurring'] = value

    @property
    def is_usable(self):
        if not (self.token or self.nonce):
            return False

        return super(BraintreePaymentMethod, self).is_usable

    @property
    def public_data(self):
        return self.data.get('details')
