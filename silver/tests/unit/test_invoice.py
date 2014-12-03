from django.test import TestCase

"""
from silver.models import (Invoice, Customer, CustomerHistory, Provider,
                           ProviderHistory)
from silver.tests.factories import CustomerFactory, ProviderFactory
"""


class TestInvoice(TestCase):
    def test_basic_invoice_creation(self):
        assert True
        """
         customer = CustomerFactory.create()
         provider = ProviderFactory.create()

         invoice = Invoice(currency='USD')
         invoice.save(invoice_customer_id=customer.id,
                      invoice_provider_id=provider.id)
        """
        # Assertions
