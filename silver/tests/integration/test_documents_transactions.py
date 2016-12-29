from django.test import TestCase
from django.test import override_settings
from mock import MagicMock, patch, call, PropertyMock
from silver.models import PaymentMethod

from silver.models import Transaction
from silver.models.payment_processors.base import PaymentProcessorBase
from silver.models.payment_processors.mixins import TriggeredProcessorMixin
from silver.tests.factories import TransactionFactory, ProformaFactory, \
    PaymentMethodFactory, InvoiceFactory


class TriggeredProcessor(PaymentProcessorBase, TriggeredProcessorMixin):
    def manage_transaction(self, transaction):
        pass


PAYMENT_PROCESSORS = {
    'manual': {
        'path': 'silver.models.payment_processors.manual.ManualProcessor',
        'display_name': 'Manual'
    },
    'triggeredprocessor': {
        'path': 'silver.tests.integration.test_documents_transactions.TriggeredProcessor',
        'display_name': 'TriggeredProcessor'
    }
}


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

    @override_settings(PAYMENT_PROCESSORS=PAYMENT_PROCESSORS)
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

        mock_manage = MagicMock()
        with patch.multiple(TriggeredProcessor, manage_transaction=mock_manage):
            invoice.issue()

            transactions = Transaction.objects.filter(
                invoice=invoice, proforma=invoice.proforma
            )
            self.assertEqual(len(transactions), 1)

            transaction = transactions[0]

            self.assertIn(call(transaction), mock_manage.call_args_list)

            self.assertEqual(mock_manage.call_count, 1)

    @override_settings(PAYMENT_PROCESSORS=PAYMENT_PROCESSORS)
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

        mock_manage = MagicMock()
        with patch.multiple(TriggeredProcessor, manage_transaction=mock_manage):
            invoice.issue()

            transactions = Transaction.objects.filter(
                invoice=invoice, proforma=invoice.proforma
            )
            self.assertEqual(len(transactions), 0)

    @override_settings(PAYMENT_PROCESSORS=PAYMENT_PROCESSORS)
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

        mock_manage = MagicMock()
        with patch.multiple(TriggeredProcessor, manage_transaction=mock_manage):
            invoice.issue()

            transactions = Transaction.objects.filter(
                invoice=invoice, proforma=invoice.proforma
            )
            self.assertEqual(len(transactions), 0)

    @override_settings(PAYMENT_PROCESSORS=PAYMENT_PROCESSORS)
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

        mock_manage = MagicMock()
        with patch.multiple(TriggeredProcessor, manage_transaction=mock_manage):
            invoice.issue()

            transactions = Transaction.objects.filter(
                payment_method=payment_method, invoice=invoice,
                proforma=proforma
            )
            self.assertEqual(len(transactions), 1)
            self.assertEqual(transactions[0], transaction)

            self.assertEqual(mock_manage.call_count, 0)
