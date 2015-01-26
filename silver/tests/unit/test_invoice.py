from django.test import TestCase

from silver.models import (Invoice)
from silver.tests.factories import CustomerFactory, ProviderFactory


class TestInvoice(TestCase):

    def _assert_common_fields_equality(self, obj1, obj2):
        obj1_fields = [field.name for field in obj1._meta.fields]
        for field in obj1_fields:
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


    def test_customer_hist_and_provider_hist_proper_update(self):
        customer = CustomerFactory.create()
        provider = ProviderFactory.create()

        invoice = Invoice(currency='USD')
        invoice.save(invoice_customer_id=customer.id,
                     invoice_provider_id=provider.id)

        customer.name = 'NewName'
        customer.address_1 = "NewAddress"
        customer.save()
        provider.name = 'NewName'
        provider.address_1 = "NewAddress"
        provider.save()

        invoice = Invoice.objects.get(id=1)
        assert invoice.customer.name == "NewName"
        assert invoice.customer.address_1 == "NewAddress"
        assert invoice.provider.name == "NewName"
        assert invoice.provider.address_1 == "NewAddress"

    def test_ignore_historical_customers_and_providers(self):
        """
        TODO: add the test after finishing fsm transitions.

        If an invoice's state is issued => the curresponding CustomerHistory
        and ProviderHistory objects should have the attribute archived=True
        => any updates on the related Customer/Provider objects should
        not influence the corresponding historical CustomerHistory/ProviderFactory
        objects.
        """
        assert True
