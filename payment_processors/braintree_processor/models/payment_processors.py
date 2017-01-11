# Copyright (c) 2017 Presslabs SRL
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging

import braintree
from braintree.exceptions import (AuthenticationError, AuthorizationError,
                                  DownForMaintenanceError, ServerError,
                                  UpgradeRequiredError)
from django_fsm import TransitionNotAllowed

from django.utils import timezone

from silver.models.payment_processors.base import PaymentProcessorBase
from silver.models.payment_processors.mixins import TriggeredProcessorMixin
from .payment_methods import BraintreePaymentMethod
from ..views import BraintreeTransactionView
from ..forms import BraintreeTransactionForm


logger = logging.getLogger(__name__)


class BraintreeTriggered(PaymentProcessorBase, TriggeredProcessorMixin):
    reference = 'braintree_triggered'
    form_class = BraintreeTransactionForm
    payment_method_class = BraintreePaymentMethod
    transaction_view_class = BraintreeTransactionView

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

    def _update_payment_method(self, payment_method, result_details,
                               instrument_type):
        """
        :param payment_method: A BraintreePaymentMethod.
        :param result_details: A (part of) braintreeSDK result(response)
                               containing payment method information.
        :param instrument_type: The type of the instrument (payment method);
                                see BraintreePaymentMethod.Types.
        :description: Updates a given payment method's data with data from a
                      braintreeSDK result payment method.
        """
        payment_method_details = {
            'type': instrument_type,
            'image_url': result_details.image_url,
            'updated_at': timezone.now().isoformat()
        }

        if instrument_type == payment_method.Types.PayPal:
            payment_method_details['email'] = result_details.payer_email
        elif instrument_type == payment_method.Types.CreditCard:
            payment_method_details.update({
                'card_type': result_details.card_type,
                'last_4': result_details.last_4,
            })

        payment_method.data['details'] = payment_method_details

        try:
            if payment_method.is_recurring:
                if not payment_method.vefified:
                    payment_method.token = result_details.token
                    payment_method.verified = True
                    payment_method.save()
            else:
                payment_method.remove()
        except TransitionNotAllowed as e:
            # TODO handle this
            pass

        payment_method.save()

    def _update_transaction_status(self, transaction, result_transaction):
        """
        :param transaction: A Transaction.
        :param result_transaction: A transaction from a braintreeSDK
                                   result(response).
        :description: Updates a given transaction's data with data from a
                      braintreeSDK result payment method.
        """
        if not transaction.data:
            transaction.data = {}

        transaction.external_reference = result_transaction.id
        status = result_transaction.status

        transaction.data['status'] = status

        try:
            transaction.process()

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

            elif status in [braintree.Transaction.Status.Settling,
                            braintree.Transaction.Status.SettlementPending,
                            braintree.Transaction.Status.Settled]:
                if transaction.state != transaction.States.Settled:
                    transaction.settle()

            return True
        except TransitionNotAllowed as e:
            # TODO handle this (probably throw something else)
            return False
        finally:
            transaction.save()

    def _update_customer(self, customer, result_details):
        if not 'braintree_id' in customer.meta:
            customer.meta['braintree_id'] = result_details.id
            customer.save()

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
            # TODO check how firstname and lastname can be obtained (for both
            # credit card and paypal)
            'options': {
                'submit_for_settlement': True,
                "store_in_vault": payment_method.is_recurring
            },
        })

        customer = transaction.customer
        if 'braintree_id' in customer.meta:
            data.update({
                'customer_id': customer.meta['braintree_id']
            })
        else:
            data.update({
                'customer': {
                    'first_name': customer.name,
                    # TODO split silver customer name field into first and last.
                    # This should've been obvious from the very start
                }
            })

        # send transaction request
        result = braintree.Transaction.sale(data)

        # handle response
        if not result.is_success or not result.transaction:
            errors = [
                error.code for error in result.errors.deep_errors
            ] if result.errors else None

            logger.warning('Couldn\'t charge Braintree transaction.: %s', {
                'message': result.message,
                'errors': errors,
                'customer_id': customer.id,
                'card_verification': (result.credit_card_verification if errors
                                      else None)
            })

            return False

        self._update_customer(customer, result.transaction.customer_details)

        instrument_type = result.transaction.payment_instrument_type

        if instrument_type == payment_method.Types.PayPal:
            details = result.transaction.paypal_details
        elif instrument_type == payment_method.Types.CreditCard:
            details = result.transaction.credit_card_details
        else:
            # Only PayPal and CreditCard are currently handled
            return False

        self._update_payment_method(
            payment_method, details, instrument_type
        )
        if not self._update_transaction_status(transaction, result.transaction):
            logger.warning('Braintree Transaction succeeded on Braintree but '
                           'not reflected locally: %s' % {
                               'transaction_id': transaction.id,
                               'transaction_uuid': transaction.uuid
                           })
            return False

        return True

    def execute_transaction(self, transaction):
        """
        :param transaction: A Braintree transaction in Initial state.
        :return: True on success, False on failure.
        """

        if not transaction.payment_processor == self:
            return False

        if transaction.state != transaction.States.Initial:
            return False

        return self._charge_transaction(transaction)

    def update_transaction_status(self, transaction):
        """
        :param transaction: A Braintree transaction in Initial or Pending state.
        :return: True on success, False on failure.
        """

        if not transaction.payment_processor == self:
            return False

        if transaction.state != transaction.States.Pending:
            return False

        if not transaction.data.get('braintree_id'):
            logger.warning('Found pending Braintree transaction with no '
                           'braintree_id: %s', {
                                'transaction_id': transaction.id,
                                'transaction_uuid': transaction.uuid
                           })

            return False

        try:
            result_transaction = braintree.Transaction.find(
                transaction.data['braintree_id']
            )
            return self._update_transaction_status(transaction,
                                                   result_transaction)
        except braintree.exceptions.NotFoundError:
            logger.warning('Couldn\'t find Braintree transaction from '
                           'Braintree %s', {
                                'braintree_id': transaction.data['braintree_id'],
                                'transaction_id': transaction.id,
                                'transaction_uuid': transaction.uuid
                           })
            return False
