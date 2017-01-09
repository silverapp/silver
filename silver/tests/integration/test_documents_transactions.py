from mock import MagicMock, patch, call, PropertyMock

from django.test import TestCase

from silver.models import PaymentMethod
from silver.models import Transaction
from silver.models.payment_processors.base import PaymentProcessorBase
from silver.models.payment_processors.mixins import TriggeredProcessorMixin
from silver.tests.factories import TransactionFactory, ProformaFactory, \
    PaymentMethodFactory, InvoiceFactory
from silver.tests.utils import register_processor


class TriggeredProcessor(PaymentProcessorBase, TriggeredProcessorMixin):
    reference = 'triggeredprocessor'

    def execute_transaction(self, transaction):
        pass


class TestDocumentsTransactions(TestCase):
    def test_pay_documents_on_transaction_settle(self):
        proforma = ProformaFactory.create()
        proforma.issue()
        proforma.save()
        invoice = proforma.create_invoice()
        transaction = TransactionFactory.create(
            state=Transaction.States.Pending,
            invoice=invoice,
            proforma=proforma
        )
        transaction.settle()
        transaction.save()

        proforma.refresh_from_db()
        invoice.refresh_from_db()

        self.assertEqual(proforma.state, proforma.STATES.PAID)
        self.assertEqual(invoice.state, invoice.STATES.PAID)

    # also refunding needs to be tested when implemented

    @register_processor(TriggeredProcessor, display_name='TriggeredProcessor')
    @patch('silver.models.payment_methods.PaymentMethod.is_recurring')
    def test_transaction_creation_for_issued_documents(self, mock_recurring):
        """
            The happy case.
        """
        invoice = InvoiceFactory.create()
        customer = invoice.customer

        PaymentMethodFactory.create(
            payment_processor='triggeredprocessor', customer=customer,
            state=PaymentMethod.States.Enabled
        )
        mock_recurring.return_value = True

        mock_execute = MagicMock()
        with patch.multiple(TriggeredProcessor, execute_transaction=mock_execute):
            invoice.issue()

            transactions = Transaction.objects.filter(
                invoice=invoice, proforma=invoice.proforma
            )
            self.assertEqual(len(transactions), 1)

            transaction = transactions[0]

            self.assertIn(call(transaction), mock_execute.call_args_list)

            self.assertEqual(mock_execute.call_count, 1)

    @register_processor(TriggeredProcessor, display_name='TriggeredProcessor')
    @patch('silver.models.payment_methods.PaymentMethod.is_recurring',
           new_callable=PropertyMock)
    def test_no_transaction_creation_for_issued_documents_case_1(self,
                                                                 mock_recurring):
        """
            The payment method is not recurring
        """
        invoice = InvoiceFactory.create()
        customer = invoice.customer

        PaymentMethodFactory.create(
            payment_processor='triggeredprocessor', customer=customer,
            state=PaymentMethod.States.Enabled
        )
        mock_recurring.return_value = False

        mock_execute = MagicMock()
        with patch.multiple(TriggeredProcessor, execute_transaction=mock_execute):
            invoice.issue()

            transactions = Transaction.objects.filter(
                invoice=invoice, proforma=invoice.proforma
            )
            self.assertEqual(len(transactions), 0)

    @register_processor(TriggeredProcessor, display_name='TriggeredProcessor')
    @patch('silver.models.payment_methods.PaymentMethod.is_recurring',
           new_callable=PropertyMock)
    @patch('silver.models.payment_methods.PaymentMethod.is_usable',
           new_callable=PropertyMock)
    def test_no_transaction_creation_for_issued_documents_case2(
        self, mock_usable, mock_recurring
    ):
        """
            The payment method is not usable
        """
        invoice = InvoiceFactory.create()
        customer = invoice.customer

        PaymentMethodFactory.create(
            payment_processor='triggeredprocessor', customer=customer,
            state=PaymentMethod.States.Enabled
        )

        mock_usable.return_value = False
        mock_recurring.return_value = True

        mock_execute = MagicMock()
        with patch.multiple(TriggeredProcessor, execute_transaction=mock_execute):
            invoice.issue()

            transactions = Transaction.objects.filter(
                invoice=invoice, proforma=invoice.proforma
            )
            self.assertEqual(len(transactions), 0)

    @register_processor(TriggeredProcessor, display_name='TriggeredProcessor')
    @patch('silver.models.payment_methods.PaymentMethod.is_recurring',
           new_callable=PropertyMock)
    def test_no_transaction_creation_for_issued_documents_case3(self,
                                                                mock_recurring):
        """
            There already is an active (initial/pending) transaction for the
            document. This can happen when the second document is triggering
            the issue transition
        """
        invoice = InvoiceFactory.create()
        customer = invoice.customer
        proforma = ProformaFactory.create(customer=customer)

        payment_method = PaymentMethodFactory.create(
            payment_processor='triggeredprocessor', customer=customer,
            state=PaymentMethod.States.Enabled
        )
        mock_recurring.return_value = True

        transaction = TransactionFactory.create(
            payment_method=payment_method, invoice=invoice, proforma=proforma
        )

        mock_execute = MagicMock()
        with patch.multiple(TriggeredProcessor, execute_transaction=mock_execute):
            invoice.issue()

            transactions = Transaction.objects.filter(
                payment_method=payment_method, invoice=invoice,
                proforma=proforma
            )
            self.assertEqual(len(transactions), 1)
            self.assertEqual(transactions[0], transaction)

            self.assertEqual(mock_execute.call_count, 0)
