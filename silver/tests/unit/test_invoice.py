from django.test import TestCase

from silver.models import DocumentEntry
from silver.tests.factories import (ProformaFactory, InvoiceFactory,
                                    DocumentEntryFactory)


class TestInvoice(TestCase):
    def test_pay_invoice_related_proforma_state_change_to_paid(self):
        proforma = ProformaFactory.create()
        proforma.issue()
        proforma.create_invoice()

        assert proforma.invoice.state == 'issued'

        proforma.invoice.pay()
        proforma.invoice.save()

        assert proforma.invoice.state == 'paid'
        assert proforma.state == 'paid'

    def test_clone_invoice_into_draft(self):
        invoice = InvoiceFactory.create()
        invoice.issue()
        invoice.pay()
        invoice.save()

        entries = DocumentEntryFactory.create_batch(3)
        invoice.invoice_entries.add(*entries)

        clone = invoice.clone_into_draft()

        assert clone.state == 'draft'
        assert clone.paid_date is None
        assert clone.issue_date is None
        assert clone.proforma is None
        assert (clone.series != invoice.series or
                clone.number != invoice.number)
        assert clone.sales_tax_percent == invoice.sales_tax_percent
        assert clone.sales_tax_name == invoice.sales_tax_name

        assert not clone.archived_customer
        assert not clone.archived_provider
        assert clone.customer == invoice.customer
        assert clone.provider == invoice.provider

        assert clone.currency == invoice.currency
        assert clone._last_state == clone.state
        assert clone.pk != invoice.pk
        assert clone.id != invoice.id
        assert not clone.pdf

        assert clone.invoice_entries.count() == 3
        assert invoice.invoice_entries.count() == 3

        entry_fields = [entry.name for entry in DocumentEntry._meta.get_fields()]
        for clone_entry, original_entry in zip(clone.invoice_entries.all(),
                                               invoice.invoice_entries.all()):
            for entry in entry_fields:
                if entry not in ('id', 'proforma', 'invoice'):
                    assert getattr(clone_entry, entry) == \
                        getattr(original_entry, entry)
        assert invoice.state == 'paid'

    def test_cancel_issued_invoice_with_related_proforma(self):
        proforma = ProformaFactory.create()
        proforma.issue()

        if not proforma.invoice:
            proforma.create_invoice()

        proforma.invoice.cancel()
        proforma.invoice.save()

        assert proforma.invoice.state == proforma.state == 'canceled'
