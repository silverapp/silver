# Copyright (c) 2015 Presslabs SRL
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import json
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from django.conf import settings
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase
from annoying.functions import get_object_or_None

from silver.models import Invoice
from silver.tests.factories import (AdminUserFactory, CustomerFactory,
                                    ProviderFactory, InvoiceFactory,
                                    SubscriptionFactory)


PAYMENT_DUE_DAYS = getattr(settings, 'SILVER_DEFAULT_DUE_DAYS', 5)


class TestInvoiceEndpoints(APITestCase):

    def setUp(self):
        admin_user = AdminUserFactory.create()
        self.client.force_authenticate(user=admin_user)

    def test_post_invoice_without_invoice_entries(self):
        CustomerFactory.create()
        ProviderFactory.create()
        SubscriptionFactory.create()

        url = reverse('invoice-list')
        data = {
            'provider': 'http://testserver/providers/1/',
            'customer': 'http://testserver/customers/1/',
            'series': "",
            'number': "",
            'currency': 'RON',
            'invoice_entries': []
        }

        response = self.client.post(url, data=data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data == {
            "id": 1,
            "series": "InvoiceSeries",
            "number": None,
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
            "invoice_entries": [],
            'pdf_url': None,
            "total": Decimal('0.00')
        }

    def test_post_invoice_with_invoice_entries(self):
        CustomerFactory.create()
        ProviderFactory.create()
        SubscriptionFactory.create()

        url = reverse('invoice-list')
        data = {
            'provider': 'http://testserver/providers/1/',
            'customer': 'http://testserver/customers/1/',
            'series': None,
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

        response = self.client.get(url + '?page=2')

        assert response.status_code == status.HTTP_200_OK

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
            "invoice_entries": [],
            "pdf_url": None,
            "total": Decimal('0.00'),
        }

    def test_delete_invoice(self):
        url = reverse('invoice-detail', kwargs={'pk': 1})

        response = self.client.delete(url)
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert response.data == {"detail": 'Method "DELETE" not allowed.'}

    def test_add_single_invoice_entry(self):
        InvoiceFactory.create_batch(10)

        url = reverse('invoice-entry-create', kwargs={'document_pk': 1})
        entry_data = {
            "description": "Page views",
            "unit_price": 10.0,
            "quantity": 20
        }
        response = self.client.post(url, data=json.dumps(entry_data),
                                    content_type='application/json')

        invoice = Invoice.objects.get(pk=1)
        total = Decimal(200.0) * Decimal(1 + invoice.sales_tax_percent / 100)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data == {
            'description': 'Page views',
            'unit': None,
            'quantity': '20.0000',
            'unit_price': '10.0000',
            'start_date': None,
            'end_date': None,
            'prorated': False,
            'product_code': None,
            'total': total,
            'total_before_tax': Decimal(200.0)
        }

        url = reverse('invoice-detail', kwargs={'pk': 1})
        response = self.client.get(url)

        invoice_entries = response.data.get('invoice_entries', None)
        assert len(invoice_entries) == 1
        assert invoice_entries[0] == {
            'description': 'Page views',
            'unit': None,
            'quantity': '20.0000',
            'unit_price': '10.0000',
            'start_date': None,
            'end_date': None,
            'prorated': False,
            'product_code': None,
            'total': total,
            'total_before_tax': Decimal(200.0)
        }

    def test_try_to_get_invoice_entries(self):
        url = reverse('invoice-entry-create', kwargs={'document_pk': 1})

        response = self.client.get(url)
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert response.data == {"detail": 'Method "GET" not allowed.'}

    def test_add_multiple_invoice_entries(self):
        InvoiceFactory.create_batch(10)

        url = reverse('invoice-entry-create', kwargs={'document_pk': 1})
        entry_data = {
            "description": "Page views",
            "unit_price": 10.0,
            "quantity": 20
        }

        invoice = Invoice.objects.get(pk=1)
        total = Decimal(200.0) * Decimal(1 + invoice.sales_tax_percent / 100)

        entries_count = 10
        for cnt in range(entries_count):
            response = self.client.post(url, data=json.dumps(entry_data),
                                        content_type='application/json')

            assert response.status_code == status.HTTP_201_CREATED
            assert response.data == {
                'description': 'Page views',
                'unit': None,
                'quantity': '20.0000',
                'unit_price': '10.0000',
                'start_date': None,
                'end_date': None,
                'prorated': False,
                'product_code': None,
                'total': total,
                'total_before_tax': Decimal(200.0)
            }

        url = reverse('invoice-detail', kwargs={'pk': 1})
        response = self.client.get(url)
        invoice_entries = response.data.get('invoice_entries', None)
        assert len(invoice_entries) == entries_count

    def test_delete_invoice_entry(self):
        InvoiceFactory.create()

        url = reverse('invoice-entry-create', kwargs={'document_pk': 1})
        entry_data = {
            "description": "Page views",
            "unit_price": 10.0,
            "quantity": 20
        }
        entries_count = 10
        for cnt in range(entries_count):
            self.client.post(url, data=json.dumps(entry_data),
                             content_type='application/json')

        url = reverse('invoice-entry-update', kwargs={'document_pk': 1,
                                                      'entry_pk': 1})
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
        entry_data = {
            "description": "Page views",
            "unit_price": 10.0,
            "quantity": 20
        }
        response = self.client.post(url, data=json.dumps(entry_data),
                                    content_type='application/json')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        msg = 'Invoice entries can be added only when the invoice is in draft state.'
        assert response.data == {'detail': msg}

        url = reverse('invoice-detail', kwargs={'pk': 1})
        response = self.client.get(url)
        invoice_entries = response.data.get('invoice_entries', None)
        assert len(invoice_entries) == 0

    def test_add_invoice_entry_in_canceled_state(self):
        invoice = InvoiceFactory.create()
        invoice.issue()
        invoice.cancel()
        invoice.save()

        url = reverse('invoice-entry-create', kwargs={'document_pk': 1})
        entry_data = {
            "description": "Page views",
            "unit_price": 10.0,
            "quantity": 20
        }
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
        entry_data = {
            "description": "Page views",
            "unit_price": 10.0,
            "quantity": 20
        }
        response = self.client.post(url, data=json.dumps(entry_data),
                                    content_type='application/json')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        msg = 'Invoice entries can be added only when the invoice is in draft state.'
        assert response.data == {'detail': msg}

        url = reverse('invoice-detail', kwargs={'pk': 1})
        response = self.client.get(url)
        invoice_entries = response.data.get('invoice_entries', None)
        assert len(invoice_entries) == 0

    def test_edit_invoice_in_issued_state(self):
        invoice = InvoiceFactory.create()
        invoice.issue()
        invoice.save()

        url = reverse('invoice-detail', kwargs={'pk': 1})
        data = {"description": "New Page views"}
        response = self.client.patch(url, data=json.dumps(data),
                                     content_type='application/json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == {'non_field_errors': [
            'You cannot edit the document once it is in issued state.']}

    def test_edit_invoice_in_canceled_state(self):
        invoice = InvoiceFactory.create()
        invoice.issue()
        invoice.cancel()
        invoice.save()

        url = reverse('invoice-detail', kwargs={'pk': 1})
        data = {"description": "New Page views"}
        response = self.client.patch(url, data=json.dumps(data),
                                     content_type='application/json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == {'non_field_errors': [
            'You cannot edit the document once it is in canceled state.']}

    def test_edit_invoice_in_paid_state(self):
        invoice = InvoiceFactory.create()
        invoice.issue()
        invoice.pay()
        invoice.save()

        url = reverse('invoice-detail', kwargs={'pk': 1})
        data = {"description": "New Page views"}
        response = self.client.patch(url, data=json.dumps(data),
                                     content_type='application/json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == {'non_field_errors': [
            'You cannot edit the document once it is in paid state.']}

    def test_issue_invoice_with_default_dates(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        InvoiceFactory.create(provider=provider, customer=customer)

        url = reverse('invoice-state', kwargs={'pk': 1})
        data = {'state': 'issued'}
        response = self.client.put(url, data=json.dumps(data),
                                   content_type='application/json')

        assert response.status_code == status.HTTP_200_OK
        due_date = timezone.now().date() + timedelta(days=PAYMENT_DUE_DAYS)
        mandatory_content = {
            'issue_date': timezone.now().date().strftime('%Y-%m-%d'),
            'due_date': due_date.strftime('%Y-%m-%d'),
            'state': 'issued'
        }
        assert response.status_code == status.HTTP_200_OK
        assert all(item in response.data.items()
                   for item in mandatory_content.iteritems())
        assert response.data.get('archived_provider', {}) != {}
        assert response.data.get('archived_customer', {}) != {}

        invoice = get_object_or_None(Invoice, pk=1)

    def test_issue_invoice_with_custom_issue_date(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        InvoiceFactory.create(provider=provider, customer=customer)

        url = reverse('invoice-state', kwargs={'pk': 1})
        data = {'state': 'issued', 'issue_date': '2014-01-01'}
        response = self.client.put(url, data=json.dumps(data),
                                   content_type='application/json')

        assert response.status_code == status.HTTP_200_OK
        due_date = timezone.now().date() + timedelta(days=PAYMENT_DUE_DAYS)
        mandatory_content = {
            'issue_date': '2014-01-01',
            'due_date': due_date.strftime('%Y-%m-%d'),
            'state': 'issued'
        }
        assert response.status_code == status.HTTP_200_OK
        assert all(item in response.data.items()
                   for item in mandatory_content.iteritems())
        assert response.data.get('archived_provider', {}) != {}
        assert response.data.get('archived_customer', {}) != {}

        invoice = get_object_or_None(Invoice, pk=1)

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

        response = self.client.put(url, data=json.dumps(data),
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

        invoice = get_object_or_None(Invoice, pk=1)

    def test_issue_invoice_when_in_issued_state(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        invoice = InvoiceFactory.create(provider=provider, customer=customer)
        invoice.issue()
        invoice.save()

        url = reverse('invoice-state', kwargs={'pk': 1})
        data = {'state': 'issued'}
        response = self.client.put(url, data=json.dumps(data),
                                   content_type='application/json')
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {
            'detail': 'An invoice can be issued only if it is in draft state.'
            }

    def test_issue_invoice_when_in_paid_state(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        invoice = InvoiceFactory.create(provider=provider, customer=customer)
        invoice.issue()
        invoice.pay()
        invoice.save()

        url = reverse('invoice-state', kwargs={'pk': 1})
        data = {'state': 'issued'}
        response = self.client.put(url, data=json.dumps(data),
                                   content_type='application/json')
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {
            'detail': 'An invoice can be issued only if it is in draft state.'
            }

    def test_pay_invoice_with_default_dates(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        invoice = InvoiceFactory.create(provider=provider, customer=customer)
        invoice.issue()
        invoice.save()

        url = reverse('invoice-state', kwargs={'pk': 1})
        data = {'state': 'paid'}
        response = self.client.put(url, data=json.dumps(data),
                                   content_type='application/json')

        assert response.status_code == status.HTTP_200_OK
        due_date = timezone.now().date() + timedelta(days=PAYMENT_DUE_DAYS)
        mandatory_content = {
            'issue_date': timezone.now().date().strftime('%Y-%m-%d'),
            'due_date': due_date.strftime('%Y-%m-%d'),
            'paid_date': timezone.now().date().strftime('%Y-%m-%d'),
            'state': 'paid'
        }
        assert response.status_code == status.HTTP_200_OK
        assert all(item in response.data.items()
                   for item in mandatory_content.iteritems())

    def test_pay_invoice_with_provided_date(self):
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
        response = self.client.put(url, data=json.dumps(data),
                                   content_type='application/json')

        assert response.status_code == status.HTTP_200_OK
        due_date = timezone.now().date() + timedelta(days=PAYMENT_DUE_DAYS)
        mandatory_content = {
            'issue_date': timezone.now().date().strftime('%Y-%m-%d'),
            'due_date': due_date.strftime('%Y-%m-%d'),
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
        response = self.client.put(url, data=json.dumps(data),
                                   content_type='application/json')
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {
            'detail': 'An invoice can be paid only if it is in issued state.'
            }

    def test_pay_invoice_when_in_paid_state(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        invoice = InvoiceFactory.create(provider=provider, customer=customer)
        invoice.issue()
        invoice.pay()
        invoice.save()

        url = reverse('invoice-state', kwargs={'pk': 1})
        data = {'state': 'paid'}
        response = self.client.put(url, data=json.dumps(data),
                                   content_type='application/json')
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {
            'detail': 'An invoice can be paid only if it is in issued state.'
            }

    def test_cancel_invoice_with_default_dates(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        invoice = InvoiceFactory.create(provider=provider, customer=customer)
        invoice.issue()
        invoice.save()

        url = reverse('invoice-state', kwargs={'pk': 1})
        data = {'state': 'canceled'}
        response = self.client.put(url, data=json.dumps(data),
                                   content_type='application/json')

        assert response.status_code == status.HTTP_200_OK
        due_date = timezone.now().date() + timedelta(days=PAYMENT_DUE_DAYS)
        mandatory_content = {
            'issue_date': timezone.now().date().strftime('%Y-%m-%d'),
            'due_date': due_date.strftime('%Y-%m-%d'),
            'cancel_date': timezone.now().date().strftime('%Y-%m-%d'),
            'state': 'canceled'
        }
        assert response.status_code == status.HTTP_200_OK
        assert all(item in response.data.items()
                   for item in mandatory_content.iteritems())

    def test_cancel_invoice_with_provided_date(self):
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

        response = self.client.put(url, data=json.dumps(data),
                                   content_type='application/json')

        assert response.status_code == status.HTTP_200_OK
        due_date = timezone.now().date() + timedelta(days=PAYMENT_DUE_DAYS)
        mandatory_content = {
            'issue_date': timezone.now().date().strftime('%Y-%m-%d'),
            'due_date': due_date.strftime('%Y-%m-%d'),
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

        response = self.client.put(url, data=json.dumps(data),
                                   content_type='application/json')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {
            'detail': 'An invoice can be canceled only if it is in issued state.'}

    def test_cancel_invoice_in_canceled_state(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        invoice = InvoiceFactory.create(provider=provider, customer=customer)
        invoice.issue()
        invoice.cancel()
        invoice.save()

        url = reverse('invoice-state', kwargs={'pk': 1})
        data = {'state': 'canceled'}

        response = self.client.put(url, data=json.dumps(data),
                                   content_type='application/json')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {
            'detail': 'An invoice can be canceled only if it is in issued state.'
            }

    def test_cancel_invoice_in_paid_state(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        invoice = InvoiceFactory.create(provider=provider, customer=customer)
        invoice.issue()
        invoice.pay()
        invoice.save()

        url = reverse('invoice-state', kwargs={'pk': 1})
        data = {'state': 'canceled'}

        response = self.client.put(url, data=json.dumps(data),
                                   content_type='application/json')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {
            'detail': 'An invoice can be canceled only if it is in issued state.'
            }

    def test_illegal_state_change_when_in_draft_state(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        InvoiceFactory.create(provider=provider, customer=customer)

        url = reverse('invoice-state', kwargs={'pk': 1})
        data = {'state': 'illegal-state'}

        response = self.client.put(url, data=json.dumps(data),
                                   content_type='application/json')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {'detail': 'Illegal state value.'}

    def test_illegal_state_change_when_in_issued_state(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        invoice = InvoiceFactory.create(provider=provider, customer=customer)
        invoice.issue()
        invoice.save()

        url = reverse('invoice-state', kwargs={'pk': 1})
        data = {'state': 'illegal-state'}

        response = self.client.put(url, data=json.dumps(data),
                                   content_type='application/json')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {'detail': 'Illegal state value.'}

    def test_illegal_state_change_when_in_paid_state(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        invoice = InvoiceFactory.create(provider=provider, customer=customer)
        invoice.issue()
        invoice.pay()
        invoice.save()

        url = reverse('invoice-state', kwargs={'pk': 1})
        data = {'state': 'illegal-state'}

        response = self.client.put(url, data=json.dumps(data),
                                   content_type='application/json')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {'detail': 'Illegal state value.'}
