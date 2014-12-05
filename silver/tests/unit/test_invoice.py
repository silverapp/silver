from django.test import TestCase

from silver.models import (Invoice, Customer, CustomerHistory, Provider,
                           ProviderHistory)
from silver.tests.factories import CustomerFactory, ProviderFactory


class TestInvoice(TestCase):

    def _assert_common_fields_equality(self, obj1, obj2):
        for field in set(obj1._meta.get_all_field_names()) - set(['id']):
            obj1_field_value = getattr(obj1, field)
            try:
                obj2_field_value = getattr(obj2, field)
                assert obj1_field_value == obj2_field_value
            except AttributeError:
                pass

    def test_basic_invoice_creation(self):
        customer = CustomerFactory.create()
        provider = ProviderFactory.create()

        invoice = Invoice(currency='USD')
        invoice.save(invoice_customer_id=customer.id,
                     invoice_provider_id=provider.id)

        customer_hist = CustomerHistory.objects.get(id=1)
        assert customer_hist.customer_ref == customer
        self._assert_common_fields_equality(customer_hist, customer)

        provider_hist = ProviderHistory.objects.get(id=1)
        assert provider_hist.provider_ref == provider
        self._assert_common_fields_equality(provider_hist, provider)
