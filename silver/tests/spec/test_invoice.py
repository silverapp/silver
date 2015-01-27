import json

from django.utils import timezone
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from silver.tests.factories import (AdminUserFactory, CustomerFactory,
                                    ProviderFactory, InvoiceFactory)


class TestInvoiceEndpoints(APITestCase):
    def setUp(self):
        admin_user = AdminUserFactory.create()
        self.client.force_authenticate(user=admin_user)

    def test_post_invoice_without_invoice_entries(self):
        CustomerFactory.create()
        ProviderFactory.create()
        url = reverse('invoice-list')

        data = {
            'provider': 'http://testserver/providers/1/',
            'customer': 'http://testserver/customers/1/',
            'number': "",
            'currency': 'RON',
            'invoice_entries': []
        }

        response = self.client.post(url, data=data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data == {
            "id": 1,
            "series": "InvoiceSeries",
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
            "proforma": None,
            "invoice_entries": []
        }

    def test_post_invoice_with_invoice_entries(self):
        CustomerFactory.create()
        ProviderFactory.create()
        url = reverse('invoice-list')
        data = {
            'provider': 'http://testserver/providers/1/',
            'customer': 'http://testserver/customers/1/',
            'number': None,
            'currency': 'RON',
            'invoice_entries': [{
                "description": "Page views",
                "unit_price": 10.0,
                "quantity": 20}]
        }

        response = self.client.post(url, data=json.dumps(data),
                                    content_type='application/json')

        assert response.status_code == status.HTTP_201_CREATED
        # TODO: Check the body of the response. There were some problems
        # related to the invoice_entries list.


    def test_get_invoices(self):
        batch_size = 50
        InvoiceFactory.create_batch(batch_size)

        url = reverse('invoice-list')
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response._headers['x-result-count'] == ('X-Result-Count',
                                                       str(batch_size))

        response = self.client.get(url + '?page=2')

        assert response.status_code == status.HTTP_200_OK
        assert response._headers['x-result-count'] == ('X-Result-Count',
                                                       str(batch_size))

    def test_get_invoice(self):
        InvoiceFactory.reset_sequence(1)
        InvoiceFactory.create()

        url = reverse('invoice-detail', kwargs={'pk': 1})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data == {
            "id": 1,
            "series": "InvoiceSeries",
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
            "proforma": None,
            "invoice_entries": []
        }

    def test_delete_invoice(self):
        url = reverse('invoice-detail', kwargs={'pk': 1})
        response = self.client.delete(url)

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_add_single_invoice_entry(self):
        InvoiceFactory.create_batch(10)

        url = reverse('invoice-entry-create', kwargs={'document_pk': 1})
        entry_data = {"description": "Page views",
                      "unit_price": 10.0,
                      "quantity": 20}
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

        url = reverse('invoice-detail', kwargs={'pk': 1})
        response = self.client.get(url)

        invoice_entries = response.data.get('invoice_entries', None)
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

    def test_add_multiple_invoice_entries(self):
        InvoiceFactory.create_batch(10)

        url = reverse('invoice-entry-create', kwargs={'document_pk': 1})
        entry_data = {"description": "Page views",
                      "unit_price": 10.0,
                      "quantity": 20}

        entries_count = 10
        for cnt in range(entries_count):
            response = self.client.post(url, data=json.dumps(entry_data),
                                        content_type='application/json')

            assert response.status_code == status.HTTP_201_CREATED
            assert response.data == {
                'entry_id': cnt + 1,
                'description': 'Page views',
                'unit': None,
                'quantity': '20.0000000000',
                'unit_price': '10.0000000000',
                'start_date': None,
                'end_date': None,
                'prorated': False,
                'product_code': None
            }

        url = reverse('invoice-detail', kwargs={'pk': 1})
        response = self.client.get(url)
        invoice_entries = response.data.get('invoice_entries', None)
        assert len(invoice_entries) == entries_count

    def test_delete_invoice_entry(self):
        InvoiceFactory.create()

        url = reverse('invoice-entry-create', kwargs={'document_pk': 1})
        entry_data = {"description": "Page views",
                      "unit_price": 10.0,
                      "quantity": 20}
        entries_count = 10
        for cnt in range(entries_count):
            self.client.post(url, data=json.dumps(entry_data),
                             content_type='application/json')

        url = reverse('invoice-entry-update', kwargs={'document_pk': 1,
                                                      'entry_id': 1})
        response = self.client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT

        url = reverse('invoice-detail', kwargs={'pk': 1})
        response = self.client.get(url)
        invoice_entries = response.data.get('invoice_entries', None)
        assert len(invoice_entries) == entries_count - 1

    def test_add_invoice_entry_in_issued_state(self):
        invoice = InvoiceFactory.create()
        invoice.issue()
        invoice.save()

        url = reverse('invoice-entry-create', kwargs={'document_pk': 1})
        entry_data = {"description": "Page views",
                      "unit_price": 10.0,
                      "quantity": 20}
        response = self.client.post(url, data=json.dumps(entry_data),
                                    content_type='application/json')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        msg = 'Invoice entries can be added only when the invoice is in draft state.'
        assert response.data == {'detail': msg}

        url = reverse('invoice-detail', kwargs={'pk': 1})
        response = self.client.get(url)
        invoice_entries = response.data.get('invoice_entries', None)
        assert len(invoice_entries) == 0

    def test_add_invoice_entry_in_paid_state(self):
        invoice = InvoiceFactory.create()
        invoice.issue()
        invoice.pay()
        invoice.save()

        url = reverse('invoice-entry-create', kwargs={'document_pk': 1})
        entry_data = {"description": "Page views",
                      "unit_price": 10.0,
                      "quantity": 20}
        response = self.client.post(url, data=json.dumps(entry_data),
                                    content_type='application/json')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        msg = 'Invoice entries can be added only when the invoice is in draft state.'
        assert response.data == {'detail': msg}

        url = reverse('invoice-detail', kwargs={'pk': 1})
        response = self.client.get(url)
        invoice_entries = response.data.get('invoice_entries', None)
        assert len(invoice_entries) == 0

    def test_issue_invoice_with_default_dates(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        InvoiceFactory.create(provider=provider, customer=customer)

        url = reverse('invoice-state', kwargs={'pk': 1})
        data = {'state': 'issued'}
        response = self.client.patch(url, data=json.dumps(data),
                                     content_type='application/json')

        assert response.status_code == status.HTTP_200_OK
        mandatory_content = {
            'issue_date': timezone.now().date().strftime('%Y-%m-%d'),
            'due_date': timezone.now().date().strftime('%Y-%m-%d'),
            'state': 'issued'
        }
        assert response.status_code == status.HTTP_200_OK
        assert all(item in response.data.items()
                   for item in mandatory_content.iteritems())
        assert response.data.get('archived_provider', {}) != {}
        assert response.data.get('archived_customer', {}) != {}

    def test_issue_invoice_with_custom_issue_date(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        InvoiceFactory.create(provider=provider, customer=customer)

        url = reverse('invoice-state', kwargs={'pk': 1})
        data = {'state': 'issued', 'issue_date': '2014-01-01'}
        response = self.client.patch(url, data=json.dumps(data),
                                     content_type='application/json')

        assert response.status_code == status.HTTP_200_OK
        mandatory_content = {
            'issue_date': '2014-01-01',
            'due_date': timezone.now().date().strftime('%Y-%m-%d'),
            'state': 'issued'
        }
        assert response.status_code == status.HTTP_200_OK
        assert all(item in response.data.items()
                   for item in mandatory_content.iteritems())
        assert response.data.get('archived_provider', {}) != {}
        assert response.data.get('archived_customer', {}) != {}

    def test_issue_invoice_with_custom_issue_date_and_due_date(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        InvoiceFactory.create(provider=provider, customer=customer)

        url = reverse('invoice-state', kwargs={'pk': 1})
        data = {
            'state': 'issued',
            'issue_date': '2014-01-01',
            'due_date': '2014-01-20'
        }

        response = self.client.patch(url, data=json.dumps(data),
                                     content_type='application/json')

        assert response.status_code == status.HTTP_200_OK
        mandatory_content = {
            'issue_date': '2014-01-01',
            'due_date': '2014-01-20',
            'state': 'issued'
        }
        assert response.status_code == status.HTTP_200_OK
        assert all(item in response.data.items()
                   for item in mandatory_content.iteritems())
        assert response.data.get('archived_provider', {}) != {}
        assert response.data.get('archived_customer', {}) != {}

    def test_issue_invoice_when_in_issued_state(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        invoice = InvoiceFactory.create(provider=provider, customer=customer)
        invoice.issue()
        invoice.save()

        url = reverse('invoice-state', kwargs={'pk': 1})
        data = {'state': 'issued'}
        response = self.client.patch(url, data=json.dumps(data),
                                     content_type='application/json')
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {'detail': 'An invoice can be issued only if it is in draft state.'}

    def test_issue_invoice_when_in_paid_state(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        invoice = InvoiceFactory.create(provider=provider, customer=customer)
        invoice.issue()
        invoice.pay()
        invoice.save()

        url = reverse('invoice-state', kwargs={'pk': 1})
        data = {'state': 'issued'}
        response = self.client.patch(url, data=json.dumps(data),
                                     content_type='application/json')
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {'detail': 'An invoice can be issued only if it is in draft state.'}

    def test_pay_invoice_default_dates(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        invoice = InvoiceFactory.create(provider=provider, customer=customer)
        invoice.issue()
        invoice.save()

        url = reverse('invoice-state', kwargs={'pk': 1})
        data = {'state': 'paid'}
        response = self.client.patch(url, data=json.dumps(data),
                                     content_type='application/json')

        assert response.status_code == status.HTTP_200_OK
        mandatory_content = {
            'issue_date': timezone.now().date().strftime('%Y-%m-%d'),
            'due_date': timezone.now().date().strftime('%Y-%m-%d'),
            'paid_date': timezone.now().date().strftime('%Y-%m-%d'),
            'state': 'paid'
        }
        assert response.status_code == status.HTTP_200_OK
        assert all(item in response.data.items()
                   for item in mandatory_content.iteritems())

    def test_pay_invoice_provided_date(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        invoice = InvoiceFactory.create(provider=provider, customer=customer)
        invoice.issue()
        invoice.save()

        url = reverse('invoice-state', kwargs={'pk': 1})
        data = {
            'state': 'paid',
            'paid_date': '2014-05-05'
        }
        response = self.client.patch(url, data=json.dumps(data),
                                     content_type='application/json')

        assert response.status_code == status.HTTP_200_OK
        mandatory_content = {
            'issue_date': timezone.now().date().strftime('%Y-%m-%d'),
            'due_date': timezone.now().date().strftime('%Y-%m-%d'),
            'paid_date': '2014-05-05',
            'state': 'paid'
        }
        assert response.status_code == status.HTTP_200_OK
        assert all(item in response.data.items()
                   for item in mandatory_content.iteritems())


    def test_pay_invoice_when_in_draft_state(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        InvoiceFactory.create(provider=provider, customer=customer)

        url = reverse('invoice-state', kwargs={'pk': 1})
        data = {'state': 'paid'}
        response = self.client.patch(url, data=json.dumps(data),
                                     content_type='application/json')
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {'detail': 'An invoice can be paid only if it is in issued state.'}

    def test_pay_invoice_when_in_paid_state(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        invoice = InvoiceFactory.create(provider=provider, customer=customer)
        invoice.issue()
        invoice.pay()
        invoice.save()

        url = reverse('invoice-state', kwargs={'pk': 1})
        data = {'state': 'paid'}
        response = self.client.patch(url, data=json.dumps(data),
                                     content_type='application/json')
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {'detail': 'An invoice can be paid only if it is in issued state.'}

    def test_cancel_invoice_with_default_dates(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        invoice = InvoiceFactory.create(provider=provider, customer=customer)
        invoice.issue()
        invoice.save()

        url = reverse('invoice-state', kwargs={'pk': 1})
        data = {'state': 'canceled'}
        response = self.client.patch(url, data=json.dumps(data),
                                     content_type='application/json')

        assert response.status_code == status.HTTP_200_OK
        mandatory_content = {
            'issue_date': timezone.now().date().strftime('%Y-%m-%d'),
            'due_date': timezone.now().date().strftime('%Y-%m-%d'),
            'cancel_date': timezone.now().date().strftime('%Y-%m-%d'),
            'state': 'canceled'
        }
        assert response.status_code == status.HTTP_200_OK
        assert all(item in response.data.items()
                   for item in mandatory_content.iteritems())

    def test_cancel_invoice_with_provider_date(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        invoice = InvoiceFactory.create(provider=provider, customer=customer)
        invoice.issue()
        invoice.save()

        url = reverse('invoice-state', kwargs={'pk': 1})
        data = {
            'state': 'canceled',
            'cancel_date': '2014-10-10'
        }

        response = self.client.patch(url, data=json.dumps(data),
                                     content_type='application/json')

        assert response.status_code == status.HTTP_200_OK
        mandatory_content = {
            'issue_date': timezone.now().date().strftime('%Y-%m-%d'),
            'due_date': timezone.now().date().strftime('%Y-%m-%d'),
            'cancel_date': '2014-10-10',
            'state': 'canceled'
        }
        assert response.status_code == status.HTTP_200_OK
        assert all(item in response.data.items()
                   for item in mandatory_content.iteritems())

    def test_cancel_invoice_in_draft_state(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        InvoiceFactory.create(provider=provider, customer=customer)

        url = reverse('invoice-state', kwargs={'pk': 1})
        data = {'state': 'canceled'}

        response = self.client.patch(url, data=json.dumps(data),
                                     content_type='application/json')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {'detail': 'An invoice can be canceled only if it is in issued state.'}

    def test_cancel_invoice_in_paid_state(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        invoice = InvoiceFactory.create(provider=provider, customer=customer)
        invoice.issue()
        invoice.pay()
        invoice.save()

        url = reverse('invoice-state', kwargs={'pk': 1})
        data = {'state': 'canceled'}

        response = self.client.patch(url, data=json.dumps(data),
                                     content_type='application/json')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {'detail': 'An invoice can be canceled only if it is in issued state.'}

    def test_illegal_state_change(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        InvoiceFactory.create(provider=provider, customer=customer)

        url = reverse('invoice-state', kwargs={'pk': 1})
        data = {'state': 'illegal-state'}

        response = self.client.patch(url, data=json.dumps(data),
                                     content_type='application/json')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {'detail': 'Illegal state value.'}
