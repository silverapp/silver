# Copyright (c) 2019 Presslabs SRL
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

from __future__ import absolute_import

import json
from datetime import timedelta
from decimal import Decimal

import pytest
from six.moves import range

from factory.django import mute_signals
from freezegun import freeze_time
from rest_framework import status
from rest_framework.reverse import reverse

from django.db.models.signals import pre_save
from django.utils import timezone
from django.utils.six import text_type
from django.conf import settings

from silver.models import Invoice, Transaction, DocumentEntry
from silver.tests.api.specs.document_entry import spec_document_entry, document_entry_definition
from silver.tests.api.specs.invoice import spec_invoice, invoice_definition
from silver.fixtures.factories import (
    CustomerFactory, ProviderFactory, InvoiceFactory,
    SubscriptionFactory, TransactionFactory, PaymentMethodFactory
)
from silver.tests.utils import build_absolute_test_url


def test_post_invoice_without_invoice_entries(authenticated_api_client, customer, provider):
    SubscriptionFactory.create()

    url = reverse('invoice-list')
    provider_url = build_absolute_test_url(reverse('provider-detail', [provider.pk]))
    customer_url = build_absolute_test_url(reverse('customer-detail', [customer.pk]))

    request_data = {
        'provider': provider_url,
        'customer': customer_url,
        'series': None,
        'number': None,
        'currency': text_type('RON'),
        'invoice_entries': []
    }

    response = authenticated_api_client.post(url, data=request_data, format='json')
    assert response.status_code == status.HTTP_201_CREATED, response.data

    invoice = Invoice.objects.get(id=response.data['id'])
    invoice_definition.check_response(invoice, response.data, request_data)


def test_post_invoice_with_invoice_entries(authenticated_api_client):
    customer = CustomerFactory.create()
    provider = ProviderFactory.create()
    SubscriptionFactory.create()

    url = reverse('invoice-list')
    provider_url = build_absolute_test_url(reverse('provider-detail', [provider.pk]))
    customer_url = build_absolute_test_url(reverse('customer-detail', [customer.pk]))

    request_data = {
        'provider': provider_url,
        'customer': customer_url,
        'series': None,
        'number': None,
        'currency': text_type('RON'),
        'transaction_xe_rate': 1,
        'invoice_entries': [{
            "description": text_type("Page views"),
            "unit_price": 10.0,
            "quantity": 20}]
    }

    response = authenticated_api_client.post(url, data=request_data, format='json')

    assert response.status_code == status.HTTP_201_CREATED, response.data

    invoice = Invoice.objects.get(id=response.data['id'])
    invoice_definition.check_response(invoice, response.data, request_data)
    assert response.data['invoice_entries']  # content already checked in previous assert


@pytest.mark.parametrize('transaction_currency', ['RON', 'USD'])
def test_post_invoice_with_invoice_entries_without_transaction_xe_rate(
    transaction_currency, authenticated_api_client
):
    customer = CustomerFactory.create()
    provider = ProviderFactory.create()
    SubscriptionFactory.create()

    url = reverse('invoice-list')
    provider_url = build_absolute_test_url(reverse('provider-detail', [provider.pk]))
    customer_url = build_absolute_test_url(reverse('customer-detail', [customer.pk]))

    request_data = {
        'provider': provider_url,
        'customer': customer_url,
        'series': None,
        'number': None,
        'currency': text_type('RON'),
        'transaction_currency': text_type(transaction_currency),
        'invoice_entries': [{
            "description": text_type("Page views"),
            "unit_price": 10.0,
            "quantity": 20}]
    }

    response = authenticated_api_client.post(url, data=request_data, format='json')

    assert response.status_code == status.HTTP_201_CREATED, response.data

    invoice = Invoice.objects.get(id=response.data['id'])
    invoice_definition.check_response(invoice, response.data, request_data)
    assert response.data['invoice_entries']  # content already checked in previous assert


def test_list_invoices(authenticated_api_client, two_pages_of_invoices):
    """Tests invoice listing as well as pagination"""

    assert len(two_pages_of_invoices) == settings.API_PAGE_SIZE * 2 > 2

    url = reverse('invoice-list')
    response = authenticated_api_client.get(url)

    assert response.status_code == status.HTTP_200_OK, response.data
    assert len(response.data) == settings.API_PAGE_SIZE
    for invoice_data in response.data:
        invoice = Invoice.objects.get(id=invoice_data['id'])
        assert invoice_data == spec_invoice(invoice)

    response = authenticated_api_client.get(url + '?page=2')

    assert response.status_code == status.HTTP_200_OK, response.data
    assert len(response.data) == settings.API_PAGE_SIZE
    for invoice_data in response.data:
        invoice = Invoice.objects.get(id=invoice_data['id'])
        assert invoice_data == spec_invoice(invoice)


@freeze_time('2019-11-10')
def test_get_invoice(authenticated_api_client, settings, issued_invoice):
    invoice = issued_invoice
    customer = issued_invoice.customer

    issued_invoice.generate_pdf()

    with mute_signals(pre_save):
        [
            TransactionFactory.create(
                state=state, invoice=issued_invoice,
                payment_method=PaymentMethodFactory(customer=customer)
            )
            for state in Transaction.States.as_list()
            if state not in [Transaction.States.Canceled,
                             Transaction.States.Refunded,
                             Transaction.States.Failed]
        ]

    url = reverse('invoice-detail', kwargs={'pk': invoice.pk})

    response = authenticated_api_client.get(url, format='json')

    assert response.status_code == status.HTTP_200_OK, response.data
    invoice_definition.check_response(invoice, response_data=response.data)


def test_delete_invoice(authenticated_api_client):
    url = reverse('invoice-detail', kwargs={'pk': 1})

    response = authenticated_api_client.delete(url)
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    assert response.data == {"detail": 'Method "DELETE" not allowed.'}


def test_add_single_invoice_entry(authenticated_api_client, invoice):
    url = reverse('invoice-entry-create', kwargs={'document_pk': invoice.pk})
    request_data = {
        "description": text_type("Page views"),
        "unit_price": 10.0,
        "quantity": 20
    }
    response = authenticated_api_client.post(url, data=json.dumps(request_data),
                                             content_type='application/json')

    invoice = Invoice.objects.all()[0]
    total = Decimal(200.0) * Decimal(1 + invoice.sales_tax_percent / 100)

    assert response.status_code == status.HTTP_201_CREATED, response.data
    entry = DocumentEntry.objects.get(id=response.data['id'])
    document_entry_definition.check_response(entry, response.data, request_data)

    url = reverse('invoice-detail', kwargs={'pk': invoice.pk})
    response = authenticated_api_client.get(url)

    invoice_entries = response.data['invoice_entries']
    assert invoice_entries == [spec_document_entry(entry)]


def test_try_to_get_invoice_entries(authenticated_api_client, invoice):
    url = reverse('invoice-entry-create', kwargs={'document_pk': invoice.pk})

    response = authenticated_api_client.get(url)
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    assert response.data == {"detail": 'Method "GET" not allowed.'}


def test_add_multiple_invoice_entries(authenticated_api_client, invoice):
    url = reverse('invoice-entry-create', kwargs={'document_pk': invoice.pk})
    request_data = {
        "description": text_type("Page views"),
        "unit_price": 10.0,
        "quantity": text_type('20.0'),
    }

    entries_count = 10
    for cnt in range(entries_count):
        response = authenticated_api_client.post(url, data=json.dumps(request_data),
                                                 content_type='application/json')

        assert response.status_code == status.HTTP_201_CREATED, response.data
        entry = DocumentEntry.objects.get(id=response.data['id'])

        document_entry_definition.check_response(entry, response.data, request_data)

    url = reverse('invoice-detail', kwargs={'pk': invoice.pk})
    response = authenticated_api_client.get(url)
    invoice_entries = response.data.get('invoice_entries', None)
    assert len(invoice_entries) == entries_count


def test_delete_invoice_entry(authenticated_api_client):
    invoice = InvoiceFactory.create()

    url = reverse('invoice-entry-create', kwargs={'document_pk': invoice.pk})
    request_data = {
        "description": text_type("Page views"),
        "unit_price": 10.0,
        "quantity": 20
    }
    entries_count = 10
    for cnt in range(entries_count):
        authenticated_api_client.post(url, data=json.dumps(request_data),
                                      content_type='application/json')

    url = reverse('invoice-entry-update', kwargs={'document_pk': invoice.pk,
                                                  'entry_pk': list(invoice._entries)[0].pk})
    response = authenticated_api_client.delete(url)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    url = reverse('invoice-detail', kwargs={'pk': invoice.pk})
    response = authenticated_api_client.get(url)
    invoice_entries = response.data.get('invoice_entries', None)
    assert len(invoice_entries) == entries_count - 1


def test_add_invoice_entry_in_issued_state(authenticated_api_client):
    invoice = InvoiceFactory.create()
    invoice.issue()

    url = reverse('invoice-entry-create', kwargs={'document_pk': invoice.pk})
    request_data = {
        "description": text_type("Page views"),
        "unit_price": 10.0,
        "quantity": 20
    }
    response = authenticated_api_client.post(url, data=json.dumps(request_data),
                                             content_type='application/json')

    assert response.status_code == status.HTTP_403_FORBIDDEN
    msg = 'Invoice entries can be added only when the invoice is in draft state.'
    assert response.data == {'detail': msg}

    url = reverse('invoice-detail', kwargs={'pk': invoice.pk})
    response = authenticated_api_client.get(url)
    invoice_entries = response.data['invoice_entries']
    assert invoice_entries == []


def test_add_invoice_entry_in_canceled_state(authenticated_api_client):
    invoice = InvoiceFactory.create()
    invoice.issue()
    invoice.cancel()

    url = reverse('invoice-entry-create', kwargs={'document_pk': invoice.pk})
    request_data = {
        "description": text_type("Page views"),
        "unit_price": 10.0,
        "quantity": 20
    }
    response = authenticated_api_client.post(url, data=json.dumps(request_data),
                                             content_type='application/json')

    assert response.status_code == status.HTTP_403_FORBIDDEN
    msg = 'Invoice entries can be added only when the invoice is in draft state.'
    assert response.data == {'detail': msg}

    url = reverse('invoice-detail', kwargs={'pk': invoice.pk})
    response = authenticated_api_client.get(url)
    invoice_entries = response.data.get('invoice_entries', None)
    assert len(invoice_entries) == 0


def test_add_invoice_entry_in_paid_state(authenticated_api_client):
    invoice = InvoiceFactory.create()
    invoice.issue()
    invoice.pay()

    url = reverse('invoice-entry-create', kwargs={'document_pk': invoice.pk})
    request_data = {
        "description": text_type("Page views"),
        "unit_price": 10.0,
        "quantity": 20
    }
    response = authenticated_api_client.post(url, data=json.dumps(request_data),
                                             content_type='application/json')

    assert response.status_code == status.HTTP_403_FORBIDDEN
    msg = 'Invoice entries can be added only when the invoice is in draft state.'
    assert response.data == {'detail': msg}

    url = reverse('invoice-detail', kwargs={'pk': invoice.pk})
    response = authenticated_api_client.get(url)
    invoice_entries = response.data.get('invoice_entries', None)
    assert len(invoice_entries) == 0


def test_edit_invoice_in_issued_state(authenticated_api_client):
    invoice = InvoiceFactory.create()
    invoice.issue()

    url = reverse('invoice-detail', kwargs={'pk': invoice.pk})
    data = {"description": "New Page views"}
    response = authenticated_api_client.patch(url, data=json.dumps(data),
                                              content_type='application/json')

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data == {
        'non_field_errors': ['You cannot edit the document once it is in issued state.']
    }


def test_edit_invoice_in_canceled_state(authenticated_api_client):
    invoice = InvoiceFactory.create()
    invoice.issue()
    invoice.cancel()

    url = reverse('invoice-detail', kwargs={'pk': invoice.pk})
    data = {"description": "New Page views"}
    response = authenticated_api_client.patch(url, data=json.dumps(data),
                                              content_type='application/json')

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data == {
        'non_field_errors': ['You cannot edit the document once it is in canceled state.']
    }


def test_edit_invoice_in_paid_state(authenticated_api_client):
    invoice = InvoiceFactory.create()
    invoice.issue()
    invoice.pay()

    url = reverse('invoice-detail', kwargs={'pk': invoice.pk})
    data = {"description": "New Page views"}
    response = authenticated_api_client.patch(url, data=json.dumps(data),
                                              content_type='application/json')

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data == {
        'non_field_errors': ['You cannot edit the document once it is in paid state.']
    }


def test_issue_invoice_with_default_dates(authenticated_api_client):
    provider = ProviderFactory.create()
    customer = CustomerFactory.create()
    invoice = InvoiceFactory.create(provider=provider, customer=customer)

    url = reverse('invoice-state', kwargs={'pk': invoice.pk})
    data = {'state': 'issued'}
    response = authenticated_api_client.put(url, data=json.dumps(data),
                                            content_type='application/json')

    assert response.status_code == status.HTTP_200_OK
    due_date = timezone.now().date() + timedelta(days=settings.SILVER_DEFAULT_DUE_DAYS)
    mandatory_content = {
        'issue_date': timezone.now().date().strftime('%Y-%m-%d'),
        'due_date': due_date.strftime('%Y-%m-%d'),
        'state': 'issued'
    }
    assert response.status_code == status.HTTP_200_OK
    assert all(item in response.data.items() for item in mandatory_content.items())
    assert response.data.get('archived_provider', {}) != {}
    assert response.data.get('archived_customer', {}) != {}


def test_issue_invoice_with_custom_issue_date(authenticated_api_client):
    provider = ProviderFactory.create()
    customer = CustomerFactory.create()
    invoice = InvoiceFactory.create(provider=provider, customer=customer)

    url = reverse('invoice-state', kwargs={'pk': invoice.pk})
    data = {'state': 'issued', 'issue_date': '2014-01-01'}
    response = authenticated_api_client.put(url, data=json.dumps(data),
                                            content_type='application/json')

    assert response.status_code == status.HTTP_200_OK
    due_date = timezone.now().date() + timedelta(days=settings.SILVER_DEFAULT_DUE_DAYS)
    mandatory_content = {
        'issue_date': '2014-01-01',
        'due_date': due_date.strftime('%Y-%m-%d'),
        'state': 'issued'
    }
    assert response.status_code == status.HTTP_200_OK
    assert all(item in list(response.data.items()) for item in mandatory_content.items())
    assert response.data.get('archived_provider', {}) != {}
    assert response.data.get('archived_customer', {}) != {}


def test_issue_invoice_with_custom_issue_date_and_due_date(authenticated_api_client):
    provider = ProviderFactory.create()
    customer = CustomerFactory.create()
    invoice = InvoiceFactory.create(provider=provider, customer=customer)

    url = reverse('invoice-state', kwargs={'pk': invoice.pk})
    data = {
        'state': 'issued',
        'issue_date': '2014-01-01',
        'due_date': '2014-01-20'
    }

    response = authenticated_api_client.put(url, data=json.dumps(data),
                                            content_type='application/json')

    assert response.status_code == status.HTTP_200_OK
    mandatory_content = {
        'issue_date': '2014-01-01',
        'due_date': '2014-01-20',
        'state': 'issued'
    }
    assert response.status_code == status.HTTP_200_OK
    assert all(item in list(response.data.items()) for item in mandatory_content.items())
    assert response.data.get('archived_provider', {}) != {}
    assert response.data.get('archived_customer', {}) != {}


def test_issue_invoice_when_in_issued_state(authenticated_api_client):
    provider = ProviderFactory.create()
    customer = CustomerFactory.create()
    invoice = InvoiceFactory.create(provider=provider, customer=customer)
    invoice.issue()

    url = reverse('invoice-state', kwargs={'pk': invoice.pk})
    data = {'state': 'issued'}
    response = authenticated_api_client.put(url, data=json.dumps(data),
                                            content_type='application/json')
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data == {
        'detail': 'An invoice can be issued only if it is in draft state.'
    }


def test_issue_invoice_when_in_paid_state(authenticated_api_client):
    provider = ProviderFactory.create()
    customer = CustomerFactory.create()
    invoice = InvoiceFactory.create(provider=provider, customer=customer)
    invoice.issue()
    invoice.pay()

    url = reverse('invoice-state', kwargs={'pk': invoice.pk})
    data = {'state': 'issued'}
    response = authenticated_api_client.put(url, data=json.dumps(data),
                                            content_type='application/json')
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data == {
        'detail': 'An invoice can be issued only if it is in draft state.'
    }


def test_pay_invoice_with_default_dates(authenticated_api_client):
    provider = ProviderFactory.create()
    customer = CustomerFactory.create()
    invoice = InvoiceFactory.create(provider=provider, customer=customer)
    invoice.issue()

    url = reverse('invoice-state', kwargs={'pk': invoice.pk})
    data = {'state': 'paid'}
    response = authenticated_api_client.put(url, data=json.dumps(data),
                                            content_type='application/json')

    assert response.status_code == status.HTTP_200_OK
    due_date = timezone.now().date() + timedelta(days=settings.SILVER_DEFAULT_DUE_DAYS)
    mandatory_content = {
        'issue_date': timezone.now().date().strftime('%Y-%m-%d'),
        'due_date': due_date.strftime('%Y-%m-%d'),
        'paid_date': timezone.now().date().strftime('%Y-%m-%d'),
        'state': 'paid'
    }
    assert response.status_code == status.HTTP_200_OK
    assert all(item in list(response.data.items())
               for item in mandatory_content.items())


def test_pay_invoice_with_provided_date(authenticated_api_client):
    provider = ProviderFactory.create()
    customer = CustomerFactory.create()
    invoice = InvoiceFactory.create(provider=provider, customer=customer)
    invoice.issue()

    url = reverse('invoice-state', kwargs={'pk': invoice.pk})
    data = {
        'state': 'paid',
        'paid_date': '2014-05-05'
    }
    response = authenticated_api_client.put(url, data=json.dumps(data),
                                            content_type='application/json')

    assert response.status_code == status.HTTP_200_OK
    due_date = timezone.now().date() + timedelta(days=settings.SILVER_DEFAULT_DUE_DAYS)
    mandatory_content = {
        'issue_date': timezone.now().date().strftime('%Y-%m-%d'),
        'due_date': due_date.strftime('%Y-%m-%d'),
        'paid_date': '2014-05-05',
        'state': 'paid'
    }
    assert response.status_code == status.HTTP_200_OK
    assert all(item in list(response.data.items())
               for item in mandatory_content.items())


def test_pay_invoice_when_in_draft_state(authenticated_api_client):
    provider = ProviderFactory.create()
    customer = CustomerFactory.create()
    invoice = InvoiceFactory.create(provider=provider, customer=customer)

    url = reverse('invoice-state', kwargs={'pk': invoice.pk})
    data = {'state': 'paid'}
    response = authenticated_api_client.put(url, data=json.dumps(data),
                                            content_type='application/json')
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data == {
        'detail': 'An invoice can be paid only if it is in issued state.'
    }


def test_pay_invoice_when_in_paid_state(authenticated_api_client):
    provider = ProviderFactory.create()
    customer = CustomerFactory.create()
    invoice = InvoiceFactory.create(provider=provider, customer=customer)
    invoice.issue()
    invoice.pay()

    url = reverse('invoice-state', kwargs={'pk': invoice.pk})
    data = {'state': 'paid'}
    response = authenticated_api_client.put(url, data=json.dumps(data),
                                            content_type='application/json')
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data == {
        'detail': 'An invoice can be paid only if it is in issued state.'
    }


def test_cancel_invoice_with_default_dates(authenticated_api_client):
    provider = ProviderFactory.create()
    customer = CustomerFactory.create()
    invoice = InvoiceFactory.create(provider=provider, customer=customer)
    invoice.issue()

    url = reverse('invoice-state', kwargs={'pk': invoice.pk})
    data = {'state': 'canceled'}
    response = authenticated_api_client.put(url, data=json.dumps(data),
                                            content_type='application/json')

    assert response.status_code == status.HTTP_200_OK
    due_date = timezone.now().date() + timedelta(days=settings.SILVER_DEFAULT_DUE_DAYS)
    mandatory_content = {
        'issue_date': timezone.now().date().strftime('%Y-%m-%d'),
        'due_date': due_date.strftime('%Y-%m-%d'),
        'cancel_date': timezone.now().date().strftime('%Y-%m-%d'),
        'state': 'canceled'
    }
    assert response.status_code == status.HTTP_200_OK
    assert all(item in list(response.data.items())
               for item in mandatory_content.items())


def test_cancel_invoice_with_provided_date(authenticated_api_client):
    provider = ProviderFactory.create()
    customer = CustomerFactory.create()
    invoice = InvoiceFactory.create(provider=provider, customer=customer)
    invoice.issue()

    url = reverse('invoice-state', kwargs={'pk': invoice.pk})
    data = {
        'state': 'canceled',
        'cancel_date': '2014-10-10'
    }

    response = authenticated_api_client.put(url, data=json.dumps(data),
                                            content_type='application/json')

    assert response.status_code == status.HTTP_200_OK
    due_date = timezone.now().date() + timedelta(days=settings.SILVER_DEFAULT_DUE_DAYS)
    mandatory_content = {
        'issue_date': timezone.now().date().strftime('%Y-%m-%d'),
        'due_date': due_date.strftime('%Y-%m-%d'),
        'cancel_date': '2014-10-10',
        'state': 'canceled'
    }
    assert response.status_code == status.HTTP_200_OK
    assert all(item in list(response.data.items())
               for item in mandatory_content.items())


def test_cancel_invoice_in_draft_state(authenticated_api_client):
    provider = ProviderFactory.create()
    customer = CustomerFactory.create()
    invoice = InvoiceFactory.create(provider=provider, customer=customer)

    url = reverse('invoice-state', kwargs={'pk': invoice.pk})
    data = {'state': 'canceled'}

    response = authenticated_api_client.put(url, data=json.dumps(data),
                                            content_type='application/json')

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data == {
        'detail': 'An invoice can be canceled only if it is in issued state.'
    }


def test_cancel_invoice_in_canceled_state(authenticated_api_client):
    provider = ProviderFactory.create()
    customer = CustomerFactory.create()
    invoice = InvoiceFactory.create(provider=provider, customer=customer)
    invoice.issue()
    invoice.cancel()

    url = reverse('invoice-state', kwargs={'pk': invoice.pk})
    data = {'state': 'canceled'}

    response = authenticated_api_client.put(url, data=json.dumps(data),
                                            content_type='application/json')

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data == {
        'detail': 'An invoice can be canceled only if it is in issued state.'
    }


def test_cancel_invoice_in_paid_state(authenticated_api_client):
    provider = ProviderFactory.create()
    customer = CustomerFactory.create()
    invoice = InvoiceFactory.create(provider=provider, customer=customer)
    invoice.issue()
    invoice.pay()

    url = reverse('invoice-state', kwargs={'pk': invoice.pk})
    data = {'state': 'canceled'}

    response = authenticated_api_client.put(url, data=json.dumps(data),
                                            content_type='application/json')

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data == {
        'detail': 'An invoice can be canceled only if it is in issued state.'
    }


def test_illegal_state_change_when_in_draft_state(authenticated_api_client):
    provider = ProviderFactory.create()
    customer = CustomerFactory.create()
    invoice = InvoiceFactory.create(provider=provider, customer=customer)

    url = reverse('invoice-state', kwargs={'pk': invoice.pk})
    data = {'state': 'illegal-state'}

    response = authenticated_api_client.put(url, data=json.dumps(data),
                                            content_type='application/json')

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data == {'detail': 'Illegal state value.'}


def test_illegal_state_change_when_in_issued_state(authenticated_api_client):
    provider = ProviderFactory.create()
    customer = CustomerFactory.create()
    invoice = InvoiceFactory.create(provider=provider, customer=customer)
    invoice.issue()

    url = reverse('invoice-state', kwargs={'pk': invoice.pk})
    data = {'state': 'illegal-state'}

    response = authenticated_api_client.put(url, data=json.dumps(data),
                                            content_type='application/json')

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data == {'detail': 'Illegal state value.'}


def test_illegal_state_change_when_in_paid_state(authenticated_api_client):
    provider = ProviderFactory.create()
    customer = CustomerFactory.create()
    invoice = InvoiceFactory.create(provider=provider, customer=customer)
    invoice.issue()
    invoice.pay()

    url = reverse('invoice-state', kwargs={'pk': invoice.pk})
    data = {'state': 'illegal-state'}

    response = authenticated_api_client.put(url, data=json.dumps(data),
                                            content_type='application/json')

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data == {'detail': 'Illegal state value.'}
