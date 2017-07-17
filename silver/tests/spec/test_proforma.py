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

from silver.models import Invoice, Proforma
from silver.tests.factories import (AdminUserFactory, CustomerFactory,
                                    ProviderFactory, ProformaFactory,
                                    SubscriptionFactory)


PAYMENT_DUE_DAYS = getattr(settings, 'SILVER_DEFAULT_DUE_DAYS', 5)


class TestProformaEndpoints(APITestCase):
    def setUp(self):
        admin_user = AdminUserFactory.create()
        self.client.force_authenticate(user=admin_user)

    def test_post_proforma_without_proforma_entries(self):
        customer = CustomerFactory.create()
        provider = ProviderFactory.create()
        SubscriptionFactory.create()

        url = reverse('proforma-list')
        data = {
            'provider': 'http://testserver/providers/%s/' % provider.pk,
            'customer': 'http://testserver/customers/%s/' % customer.pk,
            'series': "",
            'number': "",
            'currency': 'RON',
            'proforma_entries': []
        }

        response = self.client.post(url, data=data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        proforma = get_object_or_None(Proforma, id=response.data["id"])
        self.assertTrue(proforma)

        self.assertEqual(response.data, {
            "id": response.data["id"],
            "series": "ProformaSeries",
            "number": None,
            "provider": "http://testserver/providers/%s/" % provider.pk,
            "customer": "http://testserver/customers/%s/" % customer.pk,
            "archived_provider": {},
            "archived_customer": {},
            "due_date": None,
            "issue_date": None,
            "paid_date": None,
            "cancel_date": None,
            "sales_tax_name": "VAT",
            "sales_tax_percent": "1.00",
            "currency": "RON",
            "transaction_currency": proforma.transaction_currency,
            "transaction_xe_rate": (str(proforma.transaction_xe_rate)
                                    if proforma.transaction_xe_rate else None),
            "transaction_xe_date": proforma.transaction_xe_date,
            "pdf_url": None,
            "state": "draft",
            "invoice": None,
            "proforma_entries": [],
            "total": Decimal("0.00"),
            "total_in_transaction_currency": Decimal("0.00"),
            "transactions": []
        })

    def test_post_proforma_with_proforma_entries(self):
        customer = CustomerFactory.create()
        provider = ProviderFactory.create()
        SubscriptionFactory.create()

        url = reverse('proforma-list')
        data = {
            'provider': 'http://testserver/providers/%s/' % provider.pk,
            'customer': 'http://testserver/customers/%s/' % customer.pk,
            'series': None,
            'number': None,
            'currency': 'RON',
            'transaction_xe_rate': 1,
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

        response = self.client.get(url + '?page=2')

        assert response.status_code == status.HTTP_200_OK

    def test_get_proforma(self):
        ProformaFactory.reset_sequence(1)
        proforma = ProformaFactory.create()

        url = reverse('proforma-detail', kwargs={'pk': proforma.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {
            "id": proforma.pk,
            "series": "ProformaSeries",
            "number": 1,
            "provider": "http://testserver/providers/%s/" % proforma.provider.pk,
            "customer": "http://testserver/customers/%s/" % proforma.customer.pk,
            "archived_provider": {},
            "archived_customer": {},
            "due_date": None,
            "issue_date": None,
            "paid_date": None,
            "cancel_date": None,
            "sales_tax_name": "VAT",
            "sales_tax_percent": '1.00',
            "currency": "RON",
            "transaction_currency": proforma.transaction_currency,
            "transaction_xe_rate": ("%.4f" % proforma.transaction_xe_rate
                                    if proforma.transaction_xe_rate else None),
            "transaction_xe_date": proforma.transaction_xe_date,
            "pdf_url": None,
            "state": "draft",
            "invoice": None,
            "proforma_entries": [],
            "total": Decimal('0.00'),
            "total_in_transaction_currency": Decimal('0.00'),
            "transactions": []
        })

    def test_delete_proforma(self):
        url = reverse('proforma-detail', kwargs={'pk': 1})
        response = self.client.delete(url)

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert response.data == {"detail": 'Method "DELETE" not allowed.'}

    def test_add_single_proforma_entry(self):
        proforma = ProformaFactory.create()

        url = reverse('proforma-entry-create', kwargs={'document_pk': proforma.pk})
        entry_data = {
            "description": "Page views",
            "unit_price": 10.0,
            "quantity": 20
        }
        response = self.client.post(url, data=json.dumps(entry_data),
                                    content_type='application/json')

        proforma.refresh_from_db()

        total = Decimal(200.0) * Decimal(1 + proforma.sales_tax_percent / 100)

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

        url = reverse('proforma-detail', kwargs={'pk': proforma.pk})
        response = self.client.get(url)

        invoice_entries = response.data.get('proforma_entries', None)
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

    def test_try_to_get_proforma_entries(self):
        url = reverse('proforma-entry-create', kwargs={'document_pk': 1})

        response = self.client.get(url)
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert response.data == {"detail": 'Method "GET" not allowed.'}

    def test_add_multiple_proforma_entries(self):
        proforma = ProformaFactory.create()

        url = reverse('proforma-entry-create', kwargs={'document_pk': proforma.pk})
        entry_data = {
            "description": "Page views",
            "unit_price": 10.0,
            "quantity": 20
        }

        entries_count = 10
        for cnt in range(entries_count):
            response = self.client.post(url, data=json.dumps(entry_data),
                                        content_type='application/json')

            assert response.status_code == status.HTTP_201_CREATED

            proforma.refresh_from_db()
            total = Decimal(200.0) * Decimal(1 +
                                             proforma.sales_tax_percent / 100)
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

        url = reverse('proforma-detail', kwargs={'pk': proforma.pk})
        response = self.client.get(url)
        invoice_entries = response.data.get('proforma_entries', None)
        assert len(invoice_entries) == entries_count

    def test_delete_proforma_entry(self):
        proforma = ProformaFactory.create()

        url = reverse('proforma-entry-create', kwargs={'document_pk': proforma.pk})
        entry_data = {
            "description": "Page views",
            "unit_price": 10.0,
            "quantity": 20
        }
        entries_count = 10
        for cnt in range(entries_count):
            self.client.post(url, data=json.dumps(entry_data),
                             content_type='application/json')

        url = reverse('proforma-entry-update', kwargs={'document_pk': proforma.pk,
                                                       'entry_pk': list(proforma._entries)[0].pk})
        response = self.client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT

        url = reverse('proforma-detail', kwargs={'pk': proforma.pk})
        response = self.client.get(url)
        invoice_entries = response.data.get('proforma_entries', None)
        assert len(invoice_entries) == entries_count - 1

    def test_add_proforma_entry_in_issued_state(self):
        proforma = ProformaFactory.create()
        proforma.issue()

        url = reverse('proforma-entry-create', kwargs={'document_pk': proforma.pk})
        entry_data = {
            "description": "Page views",
            "unit_price": 10.0,
            "quantity": 20
        }
        response = self.client.post(url, data=json.dumps(entry_data),
                                    content_type='application/json')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        msg = 'Proforma entries can be added only when the proforma is in draft state.'
        assert response.data == {'detail': msg}

        url = reverse('proforma-detail', kwargs={'pk': proforma.pk})
        response = self.client.get(url)
        invoice_entries = response.data.get('proforma_entries', None)
        assert len(invoice_entries) == 0

    def test_add_proforma_entry_in_canceled_state(self):
        proforma = ProformaFactory.create()
        proforma.issue()
        proforma.cancel()

        url = reverse('proforma-entry-create', kwargs={'document_pk': proforma.pk})
        entry_data = {
            "description": "Page views",
            "unit_price": 10.0,
            "quantity": 20
        }
        response = self.client.post(url, data=json.dumps(entry_data),
                                    content_type='application/json')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        msg = 'Proforma entries can be added only when the proforma is in draft state.'
        assert response.data == {'detail': msg}

        url = reverse('proforma-detail', kwargs={'pk': proforma.pk})
        response = self.client.get(url)
        invoice_entries = response.data.get('proforma_entries', None)
        assert len(invoice_entries) == 0

    def test_add_proforma_entry_in_paid_state(self):
        proforma = ProformaFactory.create()
        proforma.issue()
        proforma.pay()

        url = reverse('proforma-entry-create', kwargs={'document_pk': proforma.pk})
        entry_data = {
            "description": "Page views",
            "unit_price": 10.0,
            "quantity": 20
        }
        response = self.client.post(url, data=json.dumps(entry_data),
                                    content_type='application/json')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        msg = 'Proforma entries can be added only when the proforma is in draft state.'
        assert response.data == {'detail': msg}

        url = reverse('proforma-detail', kwargs={'pk': proforma.pk})
        response = self.client.get(url)
        invoice_entries = response.data.get('proforma_entries', None)
        assert len(invoice_entries) == 0

    def test_edit_proforma_in_issued_state(self):
        proforma = ProformaFactory.create()
        proforma.issue()

        url = reverse('proforma-detail', kwargs={'pk': proforma.pk})
        data = {"description": "New Page views"}
        response = self.client.patch(url, data=json.dumps(data),
                                     content_type='application/json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        error_message = 'You cannot edit the document once it is in issued state.'
        assert response.data == {'non_field_errors': [error_message]}

    def test_edit_proforma_in_canceled_state(self):
        proforma = ProformaFactory.create()
        proforma.issue()
        proforma.cancel()

        url = reverse('proforma-detail', kwargs={'pk': proforma.pk})
        data = {"description": "New Page views"}
        response = self.client.patch(url, data=json.dumps(data),
                                     content_type='application/json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        error_message = 'You cannot edit the document once it is in canceled state.'
        assert response.data == {'non_field_errors': [error_message]}

    def test_edit_proforma_in_paid_state(self):
        proforma = ProformaFactory.create()
        proforma.issue()
        proforma.pay()

        url = reverse('proforma-detail', kwargs={'pk': proforma.pk})
        data = {"description": "New Page views"}
        response = self.client.patch(url, data=json.dumps(data),
                                     content_type='application/json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        error_message = 'You cannot edit the document once it is in paid state.'
        assert response.data == {'non_field_errors': [error_message]}

    def test_issue_proforma_with_default_dates(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        proforma = ProformaFactory.create(provider=provider, customer=customer)

        url = reverse('proforma-state', kwargs={'pk': proforma.pk})
        data = {'state': 'issued'}
        response = self.client.put(url, data=json.dumps(data), content_type='application/json')

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
        assert Invoice.objects.count() == 0

    def test_issue_proforma_with_custom_issue_date(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        proforma = ProformaFactory.create(provider=provider, customer=customer)

        url = reverse('proforma-state', kwargs={'pk': proforma.pk})
        data = {'state': 'issued', 'issue_date': '2014-01-01'}
        response = self.client.put(url, data=json.dumps(data), content_type='application/json')

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
        assert Invoice.objects.count() == 0

        proforma = get_object_or_None(Proforma, pk=1)

    def test_issue_proforma_with_custom_issue_date_and_due_date(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        proforma = ProformaFactory.create(provider=provider, customer=customer)

        url = reverse('proforma-state', kwargs={'pk': proforma.pk})
        data = {
            'state': 'issued',
            'issue_date': '2014-01-01',
            'due_date': '2014-01-20'
        }

        response = self.client.put(url, data=json.dumps(data), content_type='application/json')

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
        assert Invoice.objects.count() == 0

        proforma = get_object_or_None(Proforma, pk=1)

    def test_issue_proforma_when_in_issued_state(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        proforma = ProformaFactory.create(provider=provider, customer=customer)
        proforma.issue()

        url = reverse('proforma-state', kwargs={'pk': proforma.pk})
        data = {'state': 'issued'}
        response = self.client.put(url, data=json.dumps(data), content_type='application/json')
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {'detail': 'A proforma can be issued only if it is in draft state.'}
        assert Invoice.objects.count() == 0

    def test_issue_proforma_when_in_paid_state(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        proforma = ProformaFactory.create(provider=provider, customer=customer)
        proforma.issue()
        proforma.pay()

        url = reverse('proforma-state', kwargs={'pk': proforma.pk})
        data = {'state': 'issued'}
        response = self.client.put(url, data=json.dumps(data), content_type='application/json')
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {'detail': 'A proforma can be issued only if it is in draft state.'}
        assert Invoice.objects.count() == 1

    def test_pay_proforma_with_default_dates(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        proforma = ProformaFactory.create(provider=provider, customer=customer)
        proforma.issue()

        url = reverse('proforma-state', kwargs={'pk': proforma.pk})
        data = {'state': 'paid'}
        response = self.client.put(url, data=json.dumps(data), content_type='application/json')

        proforma.refresh_from_db()
        assert response.status_code == status.HTTP_200_OK
        due_date = timezone.now().date() + timedelta(days=PAYMENT_DUE_DAYS)
        mandatory_content = {
            'issue_date': timezone.now().date().strftime('%Y-%m-%d'),
            'due_date': due_date.strftime('%Y-%m-%d'),
            'paid_date': timezone.now().date().strftime('%Y-%m-%d'),
            'state': 'paid',
            'invoice': 'http://testserver/invoices/%s/' % proforma.invoice.pk
        }
        assert response.status_code == status.HTTP_200_OK
        assert all(item in response.data.items()
                   for item in mandatory_content.iteritems())

        invoice = Invoice.objects.all()[0]
        assert proforma.invoice == invoice
        assert invoice.proforma == proforma

        invoice = get_object_or_None(Invoice, proforma=proforma)

    def test_pay_proforma_with_provided_date(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        proforma = ProformaFactory.create(provider=provider, customer=customer)
        proforma.issue()

        url = reverse('proforma-state', kwargs={'pk': proforma.pk})
        data = {
            'state': 'paid',
            'paid_date': '2014-05-05'
        }
        response = self.client.put(url, data=json.dumps(data), content_type='application/json')

        proforma.refresh_from_db()
        assert response.status_code == status.HTTP_200_OK
        due_date = timezone.now().date() + timedelta(days=PAYMENT_DUE_DAYS)
        mandatory_content = {
            'issue_date': timezone.now().date().strftime('%Y-%m-%d'),
            'due_date': due_date.strftime('%Y-%m-%d'),
            'paid_date': '2014-05-05',
            'state': 'paid',
            'invoice': 'http://testserver/invoices/%s/' % proforma.invoice.pk
        }
        assert response.status_code == status.HTTP_200_OK
        assert all(item in response.data.items()
                   for item in mandatory_content.iteritems())

        invoice = Invoice.objects.all()[0]
        assert proforma.invoice == invoice
        assert invoice.proforma == proforma

        invoice = get_object_or_None(Invoice, proforma=proforma)

    def test_pay_proforma_when_in_draft_state(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        proforma = ProformaFactory.create(provider=provider, customer=customer)

        url = reverse('proforma-state', kwargs={'pk': proforma.pk})
        data = {'state': 'paid'}
        response = self.client.put(url, data=json.dumps(data), content_type='application/json')
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {'detail': 'A proforma can be paid only if it is in issued state.'}
        assert Invoice.objects.count() == 0

    def test_pay_proforma_when_in_paid_state(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        proforma = ProformaFactory.create(provider=provider, customer=customer)
        proforma.issue()
        proforma.pay()

        url = reverse('proforma-state', kwargs={'pk': proforma.pk})
        data = {'state': 'paid'}
        response = self.client.put(url, data=json.dumps(data), content_type='application/json')
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {'detail': 'A proforma can be paid only if it is in issued state.'}
        assert Invoice.objects.count() == 1

    def test_cancel_proforma_with_default_dates(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        proforma = ProformaFactory.create(provider=provider, customer=customer)
        proforma.issue()

        url = reverse('proforma-state', kwargs={'pk': proforma.pk})
        data = {'state': 'canceled'}
        response = self.client.put(url, data=json.dumps(data), content_type='application/json')

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
        assert Invoice.objects.count() == 0

    def test_cancel_proforma_with_provided_date(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        proforma = ProformaFactory.create(provider=provider, customer=customer)
        proforma.issue()

        url = reverse('proforma-state', kwargs={'pk': proforma.pk})
        data = {
            'state': 'canceled',
            'cancel_date': '2014-10-10'
        }

        response = self.client.put(url, data=json.dumps(data), content_type='application/json')

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
        assert Invoice.objects.count() == 0

    def test_cancel_proforma_in_draft_state(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        proforma = ProformaFactory.create(provider=provider, customer=customer)

        url = reverse('proforma-state', kwargs={'pk': proforma.pk})
        data = {'state': 'canceled'}

        response = self.client.put(url, data=json.dumps(data), content_type='application/json')

        assert response.status_code == status.HTTP_403_FORBIDDEN

        asserted_response = 'A proforma can be canceled only if it is in issued state.'
        assert response.data == {'detail': asserted_response}
        assert Invoice.objects.count() == 0

    def test_cancel_proforma_in_canceled_state(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        proforma = ProformaFactory.create(provider=provider, customer=customer)
        proforma.issue()
        proforma.cancel()

        url = reverse('proforma-state', kwargs={'pk': proforma.pk})
        data = {'state': 'canceled'}

        response = self.client.put(url, data=json.dumps(data), content_type='application/json')

        assert response.status_code == status.HTTP_403_FORBIDDEN

        asserted_response = 'A proforma can be canceled only if it is in issued state.'
        assert response.data == {'detail': asserted_response}
        assert Invoice.objects.count() == 0

    def test_cancel_proforma_in_paid_state(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        proforma = ProformaFactory.create(provider=provider, customer=customer)
        proforma.issue()
        proforma.pay()

        url = reverse('proforma-state', kwargs={'pk': proforma.pk})
        data = {'state': 'canceled'}

        response = self.client.put(url, data=json.dumps(data), content_type='application/json')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        asserted_response = 'A proforma can be canceled only if it is in issued state.'
        assert response.data == {'detail': asserted_response}
        assert Invoice.objects.count() == 1

    def test_illegal_state_change_when_in_draft_state(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        proforma = ProformaFactory.create(provider=provider, customer=customer)

        url = reverse('proforma-state', kwargs={'pk': proforma.pk})
        data = {'state': 'illegal-state'}

        response = self.client.put(url, data=json.dumps(data), content_type='application/json')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {'detail': 'Illegal state value.'}
        assert Invoice.objects.count() == 0

    def test_illegal_state_change_when_in_issued_state(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        proforma = ProformaFactory.create(provider=provider, customer=customer)
        proforma.issue()

        url = reverse('proforma-state', kwargs={'pk': proforma.pk})
        data = {'state': 'illegal-state'}

        response = self.client.put(url, data=json.dumps(data), content_type='application/json')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {'detail': 'Illegal state value.'}
        assert Invoice.objects.count() == 0

    def test_illegal_state_change_when_in_paid_state(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        proforma = ProformaFactory.create(provider=provider, customer=customer)
        proforma.issue()
        proforma.pay()

        url = reverse('proforma-state', kwargs={'pk': proforma.pk})
        data = {'state': 'illegal-state'}

        response = self.client.put(url, data=json.dumps(data), content_type='application/json')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {'detail': 'Illegal state value.'}
        assert Invoice.objects.count() == 1
