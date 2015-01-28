import json

from django.utils import timezone
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from silver.tests.factories import (AdminUserFactory, CustomerFactory,
                                    ProviderFactory, ProformaFactory)


class TestProformaEndpoints(APITestCase):
    def setUp(self):
        admin_user = AdminUserFactory.create()
        self.client.force_authenticate(user=admin_user)

    def test_post_proforma_without_proforma_entries(self):
        CustomerFactory.create()
        ProviderFactory.create()
        url = reverse('proforma-list')

        data = {
            'provider': 'http://testserver/providers/1/',
            'customer': 'http://testserver/customers/1/',
            'number': "",
            'currency': 'RON',
            'proforma_entries': []
        }

        response = self.client.post(url, data=data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data == {
            "id": 1,
            "series": "ProformaSeries",
            "number": 1,
            "provider": "http://testserver/providers/1/",
            "customer": "http://testserver/customers/1/",
            "archived_provider": {},
            "archived_customer": {},
            "due_date": None,
            "issue_date": None,
            "paid_date": None,
            "cancel_date": None,
            "sales_tax_name": "VAT",
            "sales_tax_percent": '1.00',
            "currency": "RON",
            "state": "draft",
            "invoice": None,
            "proforma_entries": []
        }

    def test_post_proforma_with_proforma_entries(self):
        CustomerFactory.create()
        ProviderFactory.create()
        url = reverse('proforma-list')
        data = {
            'provider': 'http://testserver/providers/1/',
            'customer': 'http://testserver/customers/1/',
            'number': None,
            'currency': 'RON',
            'proforma_entries': [{
                "description": "Page views",
                "unit_price": 10.0,
                "quantity": 20
            }]
        }

        response = self.client.post(url, data=json.dumps(data),
                                    content_type='application/json')

        assert response.status_code == status.HTTP_201_CREATED
        # TODO: Check the body of the response. There were some problems
        # related to the invoice_entries list.

    def test_get_proformas(self):
        batch_size = 50
        ProformaFactory.create_batch(batch_size)

        url = reverse('proforma-list')
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response._headers['x-result-count'] == ('X-Result-Count',
                                                       str(batch_size))

        response = self.client.get(url + '?page=2')

        assert response.status_code == status.HTTP_200_OK
        assert response._headers['x-result-count'] == ('X-Result-Count',
                                                       str(batch_size))

    def test_get_proforma(self):
        ProformaFactory.reset_sequence(1)
        ProformaFactory.create()

        url = reverse('proforma-detail', kwargs={'pk': 1})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data == {
            "id": 1,
            "series": "ProformaSeries",
            "number": 1,
            "provider": "http://testserver/providers/1/",
            "customer": "http://testserver/customers/1/",
            "archived_provider": {},
            "archived_customer": {},
            "due_date": None,
            "issue_date": None,
            "paid_date": None,
            "cancel_date": None,
            "sales_tax_name": "VAT",
            "sales_tax_percent": '1.00',
            "currency": "RON",
            "state": "draft",
            "invoice": None,
            "proforma_entries": []
        }

    def test_delete_proforma(self):
        url = reverse('proforma-detail', kwargs={'pk': 1})
        response = self.client.delete(url)

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert response.data == {"detail": "Method 'DELETE' not allowed."}

    def test_add_single_proforma_entry(self):
        ProformaFactory.create_batch(10)

        url = reverse('proforma-entry-create', kwargs={'document_pk': 1})
        entry_data = {
            "description": "Page views",
            "unit_price": 10.0,
            "quantity": 20
        }
        response = self.client.post(url, data=json.dumps(entry_data),
                                    content_type='application/json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data == {
            'entry_id': 1,
            'description': 'Page views',
            'unit': None,
            'quantity': '20.0000000000',
            'unit_price': '10.0000000000',
            'start_date': None,
            'end_date': None,
            'prorated': False,
            'product_code': None
        }

        url = reverse('proforma-detail', kwargs={'pk': 1})
        response = self.client.get(url)

        invoice_entries = response.data.get('proforma_entries', None)
        assert len(invoice_entries) == 1
        assert invoice_entries[0] == {
            'entry_id': 1,
            'description': 'Page views',
            'unit': None,
            'quantity': '20.0000000000',
            'unit_price': '10.0000000000',
            'start_date': None,
            'end_date': None,
            'prorated': False,
            'product_code': None
        }
