from mock import patch

from django.test import TestCase

from silver.models import Invoice, Proforma, BillingDocument, Payment
from silver.tests.factories import (ProformaFactory, InvoiceFactory,
                                    PaymentFactory)


class TestPayments(TestCase):
    def test_create_payment_when_issuing_proforma(self):
        proforma = ProformaFactory.create()
        assert not proforma.payment

        proforma.issue()

        assert proforma.payment

        payment = proforma.payment

        assert proforma.total == payment.amount

        assert payment.invoice == proforma.related_document

    def test_create_payment_when_issuing_invoice(self):
        invoice = InvoiceFactory.create()
        assert not invoice.payment

        with patch.object(Invoice, '_save_pdf', return_value=None):
            invoice.issue()

            assert invoice.payment

            payment = invoice.payment

            assert invoice.total == payment.amount

            assert payment.proforma == invoice.related_document

    def test_pay_documents_on_payment_succeed(self):
        payment = PaymentFactory.create()

        with patch.object(Invoice, '_save_pdf', return_value=None), \
                patch.object(Proforma, '_save_pdf', return_value=None):
            payment.invoice.issue()

            payment.succeed()

            assert payment.status == Payment.Status.Paid

            assert payment.invoice.state == BillingDocument.STATES.PAID
