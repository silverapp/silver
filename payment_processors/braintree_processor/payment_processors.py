import braintree
from braintree.exceptions import (AuthenticationError, AuthorizationError,
                                  DownForMaintenanceError, ServerError,
                                  UpgradeRequiredError)

from django.utils import timezone
from django_fsm import TransitionNotAllowed

from silver.models.payment_processors.base import PaymentProcessorBase
from silver.models.payment_processors.mixins import TriggeredProcessorMixin

from .payment_methods import BraintreePaymentMethod
from .views import BraintreeTransactionView


class BraintreeTriggered(PaymentProcessorBase, TriggeredProcessorMixin):
    view_class = BraintreeTransactionView
    payment_method_class = BraintreePaymentMethod

    _has_been_setup = False

    def __init__(self, *args, **kwargs):
        if BraintreeTriggered._has_been_setup:
            return

        environment = kwargs.pop('environment', None)
        braintree.Configuration.configure(environment, **kwargs)

        BraintreeTriggered._has_been_setup = True

        super(BraintreeTriggered, self).__init__(*args, **kwargs)

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

    def _update_payment_method(self, payment_method, result_payment_method):
        """
        :param payment_method: A BraintreePaymentMethod.
        :param result_payment_method: A payment method from a braintreeSDK
                                      result(response).
        :description: Updates a given payment method's data with data from a
                      braintreeSDK result payment method.
        """

        payment_method_details = {
            'type': result_payment_method.__class__.__name__
        }

        if payment_method_details['type'] == payment_method.Type.PayPal:
            payment_method_details['email'] = result_payment_method.email
        elif payment_method_details['type'] == payment_method.Type.CreditCard:
            payment_method_details.update({
                'card_type': result_payment_method.card_type,
                'last_4': result_payment_method.last_4,
            })

        payment_method_details.update({
            'image_url': payment_method.image_url,
            'added_at': timezone.now().isoformat()
        })

        payment_method.data['details'] = payment_method_details

        try:
            if payment_method.is_recurring:
                if payment_method.state == payment_method.State.Unverified:
                    payment_method.verify({
                        'token': result_payment_method.token
                    })
            else:
                payment_method.disable()
        except TransitionNotAllowed:
            # TODO handle this
            pass

        payment_method.save()

    def _update_transaction_status(self, transaction, result_transaction):
        """
        :param payment_method: A Transaction.
        :param result_payment_method: A transaction from a braintreeSDK
                                      result(response).
        :description: Updates a given transaction's data with data from a
                      braintreeSDK result payment method.
        """

        if not transaction.data:
            transaction.data = {}

        transaction.data.update({
            'status': result_transaction.status,
            'braintree_id': result_transaction.id
        })

        status = transaction.data['status']

        try:
            if status in [braintree.Transaction.Status.AuthorizationExpired,
                          braintree.Transaction.Status.SettlementDeclined,
                          braintree.Transaction.Status.Failed,
                          braintree.Transaction.Status.GatewayRejected,
                          braintree.Transaction.Status.ProcessorDeclined]:
                if transaction.state != transaction.States.Failed:
                    transaction.fail()

            elif status == braintree.Transaction.Status.Voided:
                if transaction.state != transaction.States.Canceled:
                    transaction.cancel()

            elif status in [braintree.Transaction.Status.Authorizing,
                            braintree.Transaction.Status.Authorized,
                            braintree.Transaction.Status.SubmittedForSettlement,
                            braintree.Transaction.Status.SettlementConfirmed]:
                if transaction.state != transaction.States.Pending:
                    transaction.process()

            elif status in [braintree.Transaction.Status.Settling,
                            braintree.Transaction.Status.SettlementPending,
                            braintree.Transaction.Status.Settled]:
                if transaction.state != transaction.States.Settled:
                    transaction.settle()

        except TransitionNotAllowed:
            # TODO handle this (probably throw something else)
            pass

        transaction.save()

    def _charge_transaction(self, transaction):
        """
        :param transaction: The transaction to be charged. Must have a useable
                            payment_method.
        :return: True on success, False on failure.
        """

        payment_method = transaction.payment_method

        if not payment_method.is_usable:
            return False

        # prepare payload
        if payment_method.token:
            data = {'payment_method_token': payment_method.token}
        else:
            data = {'payment_method_nonce': payment_method.nonce}

        data.update({
            'amount': transaction.amount,
            'billing': {
                'postal_code': payment_method.data.get('postal_code')
            },
            'cardholder_name': payment_method.data.get('cardholder_name'),
            'options': {
                'submit_for_settlement': True,
                "store_in_vault_on_success": payment_method.is_recurring
            },
        })

        # send transaction request
        result = braintree.Transaction.sale(data)

        # handle response
        if result.is_success and result.transaction:
            self._update_payment_method(payment_method,
                                        result.transaction.payment_method)

            self._update_transaction_status(transaction, result.transaction)

        return result.is_success

    def manage_transaction(self, transaction):
        """
        :param transaction: A Braintree transaction in Initial or Pending state.
        :return: True on success, False on failure.
        """

        if not transaction.payment_processor == self:
            return False

        if transaction.state not in [transaction.States.Initial,
                                     transaction.States.Pending]:
            return False

        if transaction.data.get('braintree_id'):
            try:
                result_transaction = braintree.Transaction.find(
                    transaction.data['braintree_id']
                )
            except braintree.exceptions.NotFoundError:
                return False

            self._update_transaction_status(transaction, result_transaction)

            return True

        return self._charge_transaction(transaction)
