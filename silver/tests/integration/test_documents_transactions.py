from django.test import TestCase

from silver.models import Transaction
from silver.tests.factories import TransactionFactory, ProformaFactory


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
