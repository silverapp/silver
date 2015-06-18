import json
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from django.conf import settings
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from silver.models import Invoice, Proforma, DocumentEntry
from silver.tests.factories import (AdminUserFactory, CustomerFactory,
                                    ProviderFactory, ProformaFactory,
                                    SubscriptionFactory, DocumentEntryFactory)
from silver.utils import get_object_or_None

PAYMENT_DUE_DAYS = getattr(settings, 'SILVER_DEFAULT_DUE_DAYS', 5)


class TestProformaEndpoints(APITestCase):
    def setUp(self):
        admin_user = AdminUserFactory.create()
        self.client.force_authenticate(user=admin_user)

    def test_post_proforma_without_proforma_entries(self):
        CustomerFactory.create()
        ProviderFactory.create()
        SubscriptionFactory.create()

        url = reverse('proforma-list')
        data = {
            'provider': 'http://testserver/providers/1/',
            'customer': 'http://testserver/customers/1/',
            'series': "",
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
            'pdf_url': None,
            "state": "draft",
            "invoice": None,
            "proforma_entries": [],
            "total": Decimal('0.00'),
        }

    def test_post_proforma_with_proforma_entries(self):
        CustomerFactory.create()
        ProviderFactory.create()
        SubscriptionFactory.create()

        url = reverse('proforma-list')
        data = {
            'provider': 'http://testserver/providers/1/',
            'customer': 'http://testserver/customers/1/',
            'series': None,
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

        response = self.client.get(url + '?page=2')

        assert response.status_code == status.HTTP_200_OK

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
            'pdf_url': None,
            "state": "draft",
            "invoice": None,
            "proforma_entries": [],
            'total': Decimal('0.00'),
        }

    def test_delete_proforma(self):
        url = reverse('proforma-detail', kwargs={'pk': 1})
        response = self.client.delete(url)

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert response.data == {"detail": 'Method "DELETE" not allowed.'}

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

        proforma = Proforma.objects.get(pk=1)

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
            'total': total
        }

        url = reverse('proforma-detail', kwargs={'pk': 1})
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
            'total': total
        }

    def test_try_to_get_proforma_entries(self):
        url = reverse('proforma-entry-create', kwargs={'document_pk': 1})

        response = self.client.get(url)
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert response.data == {"detail": 'Method "GET" not allowed.'}

    def test_add_multiple_proforma_entries(self):
        ProformaFactory.create_batch(10)

        url = reverse('proforma-entry-create', kwargs={'document_pk': 1})
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

            proforma = Proforma.objects.get(pk=1)
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
                'total': total
            }

        url = reverse('proforma-detail', kwargs={'pk': 1})
        response = self.client.get(url)
        invoice_entries = response.data.get('proforma_entries', None)
        assert len(invoice_entries) == entries_count

    def test_delete_proforma_entry(self):
        ProformaFactory.create()

        url = reverse('proforma-entry-create', kwargs={'document_pk': 1})
        entry_data = {
            "description": "Page views",
            "unit_price": 10.0,
            "quantity": 20
        }
        entries_count = 10
        for cnt in range(entries_count):
            self.client.post(url, data=json.dumps(entry_data),
                             content_type='application/json')

        url = reverse('proforma-entry-update', kwargs={'document_pk': 1,
                                                       'entry_pk': 1})
        response = self.client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT

        url = reverse('proforma-detail', kwargs={'pk': 1})
        response = self.client.get(url)
        invoice_entries = response.data.get('proforma_entries', None)
        assert len(invoice_entries) == entries_count - 1

    def test_add_proforma_entry_in_issued_state(self):
        proforma = ProformaFactory.create()
        proforma.issue()
        proforma.save()

        url = reverse('proforma-entry-create', kwargs={'document_pk': 1})
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

        url = reverse('proforma-detail', kwargs={'pk': 1})
        response = self.client.get(url)
        invoice_entries = response.data.get('proforma_entries', None)
        assert len(invoice_entries) == 0

    def test_add_proforma_entry_in_canceled_state(self):
        proforma = ProformaFactory.create()
        proforma.issue()
        proforma.cancel()
        proforma.save()

        url = reverse('proforma-entry-create', kwargs={'document_pk': 1})
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

        url = reverse('proforma-detail', kwargs={'pk': 1})
        response = self.client.get(url)
        invoice_entries = response.data.get('proforma_entries', None)
        assert len(invoice_entries) == 0

    def test_add_proforma_entry_in_paid_state(self):
        proforma = ProformaFactory.create()
        proforma.issue()
        proforma.pay()
        proforma.save()

        url = reverse('proforma-entry-create', kwargs={'document_pk': 1})
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

        url = reverse('proforma-detail', kwargs={'pk': 1})
        response = self.client.get(url)
        invoice_entries = response.data.get('proforma_entries', None)
        assert len(invoice_entries) == 0

    def test_edit_proforma_in_issued_state(self):
        proforma = ProformaFactory.create()
        proforma.issue()
        proforma.save()

        url = reverse('proforma-detail', kwargs={'pk': 1})
        data = {"description": "New Page views"}
        response = self.client.patch(url, data=json.dumps(data),
                                     content_type='application/json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == {'non_field_errors': ['You cannot edit the document once it is in issued state.']}

    def test_edit_proforma_in_canceled_state(self):
        proforma = ProformaFactory.create()
        proforma.issue()
        proforma.cancel()
        proforma.save()

        url = reverse('proforma-detail', kwargs={'pk': 1})
        data = {"description": "New Page views"}
        response = self.client.patch(url, data=json.dumps(data),
                                     content_type='application/json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == {'non_field_errors': ['You cannot edit the document once it is in canceled state.']}

    def test_edit_proforma_in_paid_state(self):
        proforma = ProformaFactory.create()
        proforma.issue()
        proforma.pay()
        proforma.save()

        url = reverse('proforma-detail', kwargs={'pk': 1})
        data = {"description": "New Page views"}
        response = self.client.patch(url, data=json.dumps(data),
                                     content_type='application/json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == {'non_field_errors': ['You cannot edit the document once it is in paid state.']}

    def test_issue_proforma_with_default_dates(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        proforma = ProformaFactory.create(provider=provider, customer=customer)

        url = reverse('proforma-state', kwargs={'pk': 1})
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
        assert Invoice.objects.count() == 0

        proforma = get_object_or_None(Proforma, pk=1)

    def test_issue_proforma_with_custom_issue_date(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        ProformaFactory.create(provider=provider, customer=customer)

        url = reverse('proforma-state', kwargs={'pk': 1})
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
        assert Invoice.objects.count() == 0

        proforma = get_object_or_None(Proforma, pk=1)

    def test_issue_proforma_with_custom_issue_date_and_due_date(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        ProformaFactory.create(provider=provider, customer=customer)

        url = reverse('proforma-state', kwargs={'pk': 1})
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
        assert Invoice.objects.count() == 0

        proforma = get_object_or_None(Proforma, pk=1)

    def test_issue_proforma_when_in_issued_state(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        proforma = ProformaFactory.create(provider=provider, customer=customer)
        proforma.issue()
        proforma.save()

        url = reverse('proforma-state', kwargs={'pk': 1})
        data = {'state': 'issued'}
        response = self.client.put(url, data=json.dumps(data),
                                     content_type='application/json')
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {'detail': 'A proforma can be issued only if it is in draft state.'}
        assert Invoice.objects.count() == 0

    def test_issue_proforma_when_in_paid_state(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        proforma = ProformaFactory.create(provider=provider, customer=customer)
        proforma.issue()
        proforma.pay()
        proforma.save()

        url = reverse('proforma-state', kwargs={'pk': 1})
        data = {'state': 'issued'}
        response = self.client.put(url, data=json.dumps(data),
                                     content_type='application/json')
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {'detail': 'A proforma can be issued only if it is in draft state.'}
        assert Invoice.objects.count() == 1

    def test_pay_proforma_with_default_dates(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        proforma = ProformaFactory.create(provider=provider, customer=customer)
        proforma.issue()
        proforma.save()

        url = reverse('proforma-state', kwargs={'pk': 1})
        data = {'state': 'paid'}
        response = self.client.put(url, data=json.dumps(data),
                                     content_type='application/json')

        assert response.status_code == status.HTTP_200_OK
        due_date = timezone.now().date() + timedelta(days=PAYMENT_DUE_DAYS)
        mandatory_content = {
            'issue_date': timezone.now().date().strftime('%Y-%m-%d'),
            'due_date': due_date.strftime('%Y-%m-%d'),
            'paid_date': timezone.now().date().strftime('%Y-%m-%d'),
            'state': 'paid',
            'invoice': 'http://testserver/invoices/1/'
        }
        assert response.status_code == status.HTTP_200_OK
        assert all(item in response.data.items()
                   for item in mandatory_content.iteritems())

        invoice = get_object_or_None(Invoice, pk=1)
        proforma = get_object_or_None(Proforma, pk=1)
        assert proforma.invoice == invoice
        assert invoice.proforma == proforma

        invoice = get_object_or_None(Invoice, proforma=proforma)


    def test_pay_proforma_with_provided_date(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        proforma = ProformaFactory.create(provider=provider, customer=customer)
        proforma.issue()
        proforma.save()

        url = reverse('proforma-state', kwargs={'pk': 1})
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
            'state': 'paid',
            'invoice': 'http://testserver/invoices/1/'
        }
        assert response.status_code == status.HTTP_200_OK
        assert all(item in response.data.items()
                   for item in mandatory_content.iteritems())

        invoice = get_object_or_None(Invoice, pk=1)
        proforma = get_object_or_None(Proforma, pk=1)
        assert proforma.invoice == invoice
        assert invoice.proforma == proforma

        invoice = get_object_or_None(Invoice, proforma=proforma)

    def test_pay_proforma_when_in_draft_state(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        ProformaFactory.create(provider=provider, customer=customer)

        url = reverse('proforma-state', kwargs={'pk': 1})
        data = {'state': 'paid'}
        response = self.client.put(url, data=json.dumps(data),
                                     content_type='application/json')
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {'detail': 'A proforma can be paid only if it is in issued state.'}
        assert Invoice.objects.count() == 0

    def test_pay_proforma_when_in_paid_state(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        proforma = ProformaFactory.create(provider=provider, customer=customer)
        proforma.issue()
        proforma.pay()
        proforma.save()

        url = reverse('proforma-state', kwargs={'pk': 1})
        data = {'state': 'paid'}
        response = self.client.put(url, data=json.dumps(data),
                                     content_type='application/json')
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {'detail': 'A proforma can be paid only if it is in issued state.'}
        assert Invoice.objects.count() == 1

    def test_cancel_proforma_with_default_dates(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        proforma = ProformaFactory.create(provider=provider, customer=customer)
        proforma.issue()
        proforma.save()

        url = reverse('proforma-state', kwargs={'pk': 1})
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
        assert Invoice.objects.count() == 0

    def test_cancel_proforma_with_provided_date(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        proforma = ProformaFactory.create(provider=provider, customer=customer)
        proforma.issue()
        proforma.save()

        url = reverse('proforma-state', kwargs={'pk': 1})
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
        assert Invoice.objects.count() == 0

    def test_cancel_proforma_in_draft_state(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        ProformaFactory.create(provider=provider, customer=customer)

        url = reverse('proforma-state', kwargs={'pk': 1})
        data = {'state': 'canceled'}

        response = self.client.put(url, data=json.dumps(data),
                                     content_type='application/json')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {'detail': 'A proforma can be canceled only if it is in issued state.'}
        assert Invoice.objects.count() == 0

    def test_cancel_proforma_in_canceled_state(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        proforma = ProformaFactory.create(provider=provider, customer=customer)
        proforma.issue()
        proforma.cancel()
        proforma.save()

        url = reverse('proforma-state', kwargs={'pk': 1})
        data = {'state': 'canceled'}

        response = self.client.put(url, data=json.dumps(data),
                                     content_type='application/json')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {'detail': 'A proforma can be canceled only if it is in issued state.'}
        assert Invoice.objects.count() == 0

    def test_cancel_proforma_in_paid_state(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        proforma = ProformaFactory.create(provider=provider, customer=customer)
        proforma.issue()
        proforma.pay()
        proforma.save()

        url = reverse('proforma-state', kwargs={'pk': 1})
        data = {'state': 'canceled'}

        response = self.client.put(url, data=json.dumps(data),
                                     content_type='application/json')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {'detail': 'A proforma can be canceled only if it is in issued state.'}
        assert Invoice.objects.count() == 1

    def test_illegal_state_change_when_in_draft_state(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        ProformaFactory.create(provider=provider, customer=customer)

        url = reverse('proforma-state', kwargs={'pk': 1})
        data = {'state': 'illegal-state'}

        response = self.client.put(url, data=json.dumps(data),
                                     content_type='application/json')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {'detail': 'Illegal state value.'}
        assert Invoice.objects.count() == 0

    def test_illegal_state_change_when_in_issued_state(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        proforma = ProformaFactory.create(provider=provider, customer=customer)
        proforma.issue()
        proforma.save()

        url = reverse('proforma-state', kwargs={'pk': 1})
        data = {'state': 'illegal-state'}

        response = self.client.put(url, data=json.dumps(data),
                                     content_type='application/json')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {'detail': 'Illegal state value.'}
        assert Invoice.objects.count() == 0

    def test_illegal_state_change_when_in_paid_state(self):
        provider = ProviderFactory.create()
        customer = CustomerFactory.create()
        proforma = ProformaFactory.create(provider=provider, customer=customer)
        proforma.issue()
        proforma.pay()
        proforma.save()

        url = reverse('proforma-state', kwargs={'pk': 1})
        data = {'state': 'illegal-state'}

        response = self.client.put(url, data=json.dumps(data),
                                     content_type='application/json')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {'detail': 'Illegal state value.'}
        assert Invoice.objects.count() == 1

    def test_pay_proforma_related_invoice_state_change_to_paid(self):
        proforma = ProformaFactory.create()
        proforma.issue()
        proforma.create_invoice()

        proforma.pay()
        proforma.save()

        assert proforma.invoice.state == 'paid'
        assert proforma.state == 'paid'

    def test_clone_proforma_into_draft(self):
        proforma = ProformaFactory.create()
        proforma.issue()
        proforma.pay()
        proforma.save()

        entries = DocumentEntryFactory.create_batch(3)
        proforma.proforma_entries.add(*entries)

        clone = proforma.clone_into_draft()

        assert clone.state == 'draft'
        assert clone.paid_date is None
        assert clone.issue_date is None
        assert clone.invoice is None
        assert (clone.series != proforma.series or
                clone.number != proforma.number)
        assert clone.sales_tax_percent == proforma.sales_tax_percent
        assert clone.sales_tax_name == proforma.sales_tax_name

        assert not clone.archived_customer
        assert not clone.archived_provider
        assert clone.customer == proforma.customer
        assert clone.provider == proforma.provider

        assert clone.currency == proforma.currency
        assert clone._last_state == clone.state
        assert clone.pk != proforma.pk
        assert clone.id != proforma.id
        assert not clone.pdf

        assert clone.proforma_entries.count() == 3
        assert proforma.proforma_entries.count() == 3

        entry_fields = [entry.name for entry in DocumentEntry._meta.get_fields()]
        for clone_entry, original_entry in zip(clone.proforma_entries.all(),
                                               proforma.proforma_entries.all()):
            for entry in entry_fields:
                if entry not in ('id', 'proforma', 'invoice'):
                    assert getattr(clone_entry, entry) == \
                        getattr(original_entry, entry)

        assert proforma.state == 'paid'

    def test_cancel_issued_proforma_with_related_invoice(self):
        proforma = ProformaFactory.create()
        proforma.issue()

        if not proforma.invoice:
            proforma.create_invoice()

        proforma.cancel()
        proforma.save()

        assert proforma.state == proforma.invoice.state == 'canceled'
