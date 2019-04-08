import pytest

from silver.tests.factories import BillingLogFactory


@pytest.mark.django_db
def test_update_billing_log_when_creating_proforma_related_invoice():
    billing_log = BillingLogFactory.create(invoice=None)
    proforma = billing_log.proforma

    assert billing_log.invoice is None

    invoice = proforma.create_invoice()
    billing_log.refresh_from_db()
    assert billing_log.invoice == invoice
