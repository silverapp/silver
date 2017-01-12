from braintree import Transaction as BraintreeTransaction
from cryptography.fernet import Fernet
from django.conf import settings
from mock import patch

from django.test import TestCase
from silver.models import Transaction

from .factories import BraintreeTransactionFactory


class TestBraintreeTransactions(TestCase):
    def setUp(self):
        settings.PAYMENT_METHOD_SECRET = bytes(Fernet.generate_key())

        class Object(object):
            pass

        transaction = Object()
        transaction.amount = 1000
        transaction.status = BraintreeTransaction.Status.Settled
        transaction.id = 'beertrain'
        transaction.processor_response_code = 2000
        transaction.payment_instrument_type = 'paypal_account'

        transaction.paypal_details = Object()
        transaction.paypal_details.image_url = 'image_url'
        transaction.paypal_details.payer_email = 'payer_email'
        transaction.paypal_details.token = 'kento'

        transaction.customer_details = Object()
        transaction.customer_details.id = 'braintree_id'

        self.transaction = transaction

        result = Object()
        result.is_success = True
        result.transaction = transaction
        self.result = result

    def test_update_status_transaction_settle(self):
        transaction = BraintreeTransactionFactory.create(
            state=Transaction.States.Pending, data={
                'braintree_id': 'beertrain'
            }
        )

        with patch('braintree.Transaction.find') as find_mock:
            find_mock.return_value = self.transaction
            transaction.payment_processor.update_transaction_status(transaction)

            self.assertEqual(transaction.state, transaction.States.Settled)

    def test_update_status_transaction_fail(self):
        self.transaction.status = BraintreeTransaction.Status.ProcessorDeclined
        transaction = BraintreeTransactionFactory.create(
            state=Transaction.States.Pending, data={
                'braintree_id': 'beertrain'
            }
        )
        with patch('braintree.Transaction.find') as find_mock:
            find_mock.return_value = self.transaction
            transaction.payment_processor.update_transaction_status(transaction)

            self.assertEqual(transaction.state, transaction.States.Failed)

    def test_execute_transaction(self):
        transaction = BraintreeTransactionFactory.create()
        payment_method = transaction.payment_method
        payment_method.nonce = 'some-nonce'
        payment_method.is_recurring = True
        payment_method.save()

        with patch('braintree.Transaction.sale') as sale_mock:
            sale_mock.return_value = self.result
            transaction.payment_processor.execute_transaction(transaction)

            self.assertEqual(transaction.state, transaction.States.Settled)

            payment_method = transaction.payment_method
            self.assertEqual(payment_method.token,
                             self.transaction.paypal_details.token)
            self.assertEqual(payment_method.data.get('details'), {
                'image_url': self.transaction.paypal_details.image_url,
                'email': self.transaction.paypal_details.payer_email,
                'type': self.transaction.payment_instrument_type,
            })
            self.assertEqual(payment_method.verified, True)

            customer = transaction.customer
            self.assertEqual(customer.meta.get('braintree_id'),
                             self.transaction.customer_details.id)
