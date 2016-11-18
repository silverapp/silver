from django.test import TestCase
from django_fsm import TransitionNotAllowed
from silver.models import Transaction, Payment
from silver.tests.factories import TransactionFactory, PaymentFactory

TStates = Transaction.State
PStates = Payment.Status

class TestTransactionStates(TestCase):

    def test_transaction_succeed(self):
        payment = PaymentFactory.create()
        transaction = TransactionFactory.create(payment=payment)
        transaction.pending()
        self.assertEquals(payment.status, PStates.Pending)
        transaction.succeed()
        self.assertEquals(payment.status, PStates.Paid)

    def test_cancel_transaction(self):
        payment = PaymentFactory.create()
        transaction = TransactionFactory.create(payment=payment)
        self.assertEquals(transaction.status, TStates.Uninitialized)
        transaction.pending()
        self.assertEquals(transaction.status, TStates.Pending)
        self.assertEquals(payment.status, PStates.Pending)
        transaction.cancel()
        self.assertEquals(payment.status, PStates.Unpaid)

    def test_transaction_fail(self):
        payment = PaymentFactory.create()
        transaction = TransactionFactory.create(payment=payment)
        transaction.pending()
        self.assertEquals(payment.status, PStates.Pending)
        transaction.fail()
        self.assertEquals(payment.status, PStates.Unpaid)


    def test_2_transactions(self):
        payment = PaymentFactory.create()
        transaction1 = TransactionFactory.create(payment=payment)
        transaction2 = TransactionFactory.create(payment=payment)

        transaction2.pending()
        self.assertRaises(TransitionNotAllowed, transaction1.pending)
        self.assertEquals(transaction2.status, TStates.Pending)
