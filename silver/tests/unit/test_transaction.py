from django.test import TestCase
from django_fsm import TransitionNotAllowed
from silver.models import Transaction, Payment
from silver.tests.factories import TransactionFactory, PaymentFactory

PStates = Payment.Status
TStates = Transaction.States

class TestTransactionStates(TestCase):

    def test_transaction_succeed(self):
        payment = PaymentFactory.create(status=PStates.Pending)
        transaction = TransactionFactory.create(payment=payment, status=TStates.Pending)
        transaction.succeed()
        self.assertEquals(payment.status, PStates.Paid)

    def test_transaction_pending(self):
        payment = PaymentFactory.create()
        transaction = TransactionFactory.create(payment=payment)
        transaction.process()
        self.assertEquals(payment.status, PStates.Pending)

    def test_transaction_not_allowed_at_fail(self):
        payment = PaymentFactory.create()
        transaction = TransactionFactory.create(payment=payment, status=TStates.Pending)
        self.assertRaises(TransitionNotAllowed, transaction.fail)

    def test_transaction_not_allowed_at_cancel(self):
        payment = PaymentFactory.create()
        transaction = TransactionFactory.create(payment=payment, status=TStates.Uninitialized)
        self.assertRaises(TransitionNotAllowed, transaction.cancel)

    def test_transaction_not_allowed_at_process(self):
        payment = PaymentFactory.create()
        transaction = TransactionFactory.create(payment=payment, status=TStates.Canceled)
        self.assertRaises(TransitionNotAllowed, transaction.process)

    def test_cancel_transaction(self):
        payment = PaymentFactory.create()
        transaction = TransactionFactory.create(payment=payment)
        transaction.process()
        self.assertEquals(payment.status, PStates.Pending)
        transaction.cancel()
        self.assertEquals(payment.status, PStates.Unpaid)

    def test_transaction_fail(self):
        payment = PaymentFactory.create()
        transaction = TransactionFactory.create(payment=payment)
        transaction.process()
        self.assertEquals(payment.status, PStates.Pending)
        transaction.fail()
        self.assertEquals(payment.status, PStates.Unpaid)

    def test_2_transactions(self):
        payment = PaymentFactory.create()
        transaction1 = TransactionFactory.create(payment=payment)
        transaction2 = TransactionFactory.create(payment=payment)
        transaction2.process()
        self.assertRaises(TransitionNotAllowed, transaction1.process)
