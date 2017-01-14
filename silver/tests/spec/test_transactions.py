# Copyright (c) 2017 Presslabs SRL
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

from datetime import datetime, timedelta
from collections import OrderedDict
from decimal import Decimal

from rest_framework import status
from rest_framework.reverse import reverse as _reverse
from rest_framework.test import APITestCase

from django.utils import timezone

from silver.models import Transaction
from silver.models.payment_processors.base import PaymentProcessorBase
from silver.models.payment_processors.mixins import TriggeredProcessorMixin

from silver.tests.factories import (AdminUserFactory, TransactionFactory,
                                    PaymentMethodFactory, InvoiceFactory,
                                    ProformaFactory, CustomerFactory)
from silver.tests.utils import register_processor


def reverse(*args, **kwargs):
    return u'http://testserver' + _reverse(*args, **kwargs)


class SomeProcessor(PaymentProcessorBase, TriggeredProcessorMixin):
    reference = 'someprocessor'


class TestTransactionEndpoint(APITestCase):
    def setUp(self):
        self.user = AdminUserFactory.create()
        self.client.force_authenticate(user=self.user)

    def test_get_transaction(self):
        customer = CustomerFactory.create()
        payment_method = PaymentMethodFactory.create(customer=customer)

        transaction = TransactionFactory.create(payment_method=payment_method)
        invoice = transaction.invoice
        proforma = transaction.proforma
        provider = invoice.provider

        expected = OrderedDict([
            ('id', unicode(transaction.uuid)),
            ('url', reverse('transaction-detail',
                            kwargs={'customer_pk': customer.id, 'transaction_uuid': transaction.uuid})),
            ('customer', reverse('customer-detail', args=[customer.pk])),
            ('provider', reverse('provider-detail', args=[provider.pk])),
            ('amount', unicode(Decimal('0.00') + transaction.amount)),
            ('currency', unicode(transaction.currency)),
            ('currency_rate_date', None),
            ('state', unicode(transaction.state)),
            ('proforma', reverse('proforma-detail', args=[proforma.pk])),
            ('invoice', reverse('invoice-detail', args=[invoice.pk])),
            ('can_be_consumed', transaction.can_be_consumed),
            ('payment_processor', reverse('payment-processor-detail', args=[payment_method.payment_processor.reference])),
            ('payment_method', reverse('payment-method-detail', kwargs={'customer_pk': customer.id,
                                                                        'payment_method_id': payment_method.id})),
            ('pay_url', reverse('pay-transaction', kwargs={'transaction_uuid': transaction.uuid})),
            ('valid_until', None),
            ('success_url', transaction.success_url),
            ('failed_url', transaction.failed_url)
        ])

        url = reverse('transaction-detail',
                      kwargs={'customer_pk': customer.pk,
                              'transaction_uuid': transaction.uuid})
        response = self.client.get(url, format='json')

        self.assertEqual(response.data, dict(expected))

    def test_list_transactions(self):
        customer = CustomerFactory.create()
        payment_method = PaymentMethodFactory.create(customer=customer)
        transaction_1 = TransactionFactory.create(payment_method=payment_method)
        invoice_1 = transaction_1.invoice
        proforma_1 = transaction_1.proforma
        provider_1 = invoice_1.provider

        expected_t1 = OrderedDict([
            ('id', unicode(transaction_1.uuid)),
            ('url', reverse('transaction-detail',
                            kwargs={'customer_pk': customer.id, 'transaction_uuid': transaction_1.uuid})),
            ('customer', reverse('customer-detail', args=[customer.pk])),
            ('provider', reverse('provider-detail', args=[provider_1.pk])),
            ('amount', unicode(Decimal('0.00') + transaction_1.amount)),
            ('currency', unicode(transaction_1.currency)),
            ('currency_rate_date', None),
            ('state', unicode(transaction_1.state)),
            ('proforma', reverse('proforma-detail', args=[proforma_1.pk])),
            ('invoice', reverse('invoice-detail', args=[invoice_1.pk])),
            ('can_be_consumed', transaction_1.can_be_consumed),
            ('payment_processor', reverse('payment-processor-detail', args=[payment_method.payment_processor.reference])),
            ('payment_method', reverse('payment-method-detail', kwargs={'customer_pk': customer.id,
                                                                        'payment_method_id': payment_method.id})),
            ('pay_url', reverse('pay-transaction', kwargs={'transaction_uuid': transaction_1.uuid})),
            ('valid_until', None),
            ('success_url', transaction_1.success_url),
            ('failed_url', transaction_1.failed_url)
        ])

        transaction_2 = TransactionFactory.create(payment_method=payment_method)
        invoice_2 = transaction_2.invoice
        proforma_2 = transaction_2.proforma
        provider_2 = invoice_2.provider
        expected_t2 = OrderedDict([
            ('id', unicode(transaction_2.uuid)),
            ('url', reverse('transaction-detail',
                            kwargs={'customer_pk': customer.id, 'transaction_uuid': transaction_2.uuid})),
            ('customer', reverse('customer-detail', args=[customer.pk])),
            ('provider', reverse('provider-detail', args=[provider_2.pk])),
            ('amount', unicode(Decimal('0.00') + transaction_2.amount)),
            ('currency', unicode(transaction_2.currency)),
            ('currency_rate_date', None),
            ('state', unicode(transaction_2.state)),
            ('proforma', reverse('proforma-detail', args=[proforma_2.pk])),
            ('invoice', reverse('invoice-detail', args=[invoice_2.pk])),
            ('can_be_consumed', transaction_2.can_be_consumed),
            ('payment_processor', reverse('payment-processor-detail', args=[payment_method.payment_processor.reference])),
            ('payment_method', reverse('payment-method-detail', kwargs={'customer_pk': customer.id,
                                                                        'payment_method_id': payment_method.id})),
            ('pay_url', reverse('pay-transaction', kwargs={'transaction_uuid': transaction_2.uuid})),
            ('valid_until', None),
            ('success_url', transaction_2.success_url),
            ('failed_url', transaction_2.failed_url)
        ])

        url = reverse('transaction-list',
                      kwargs={'customer_pk': customer.pk})

        response = self.client.get(url, format='json')
        self.assertEqual(response.data[0], expected_t1)
        self.assertEqual(response.data[1], expected_t2)

    def test_add_transaction(self):
        customer = CustomerFactory.create()
        payment_method = PaymentMethodFactory.create(customer=customer)
        proforma = ProformaFactory.create(customer=customer)
        proforma.state = proforma.STATES.ISSUED
        proforma.create_invoice()
        proforma.refresh_from_db()
        invoice = proforma.invoice

        payment_method_url = reverse('payment-method-detail', kwargs={'customer_pk': customer.pk,
                                                                      'payment_method_id': payment_method.id})
        invoice_url = reverse('invoice-detail', args=[invoice.pk])
        proforma_url = reverse('proforma-detail', args=[proforma.pk])

        url = reverse('payment-method-transaction-list',
                      kwargs={'customer_pk': customer.pk, 'payment_method_id': payment_method.pk})
        valid_until = datetime.now() + timedelta(minutes=30)
        currency = 'USD'
        data = {
            'payment_method': reverse('payment-method-detail', kwargs={'customer_pk': customer.pk,
                                                                       'payment_method_id': payment_method.id}),
            'amount': '200.0',
            'invoice': invoice_url,
            'proforma': proforma_url,
            'valid_until': valid_until,
            'currency': currency,
            'success_url': 'http://success.url',
            'failed_url': 'http://fauiled.url'
        }

        response = self.client.post(url, format='json', data=data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(response.data['payment_method'], payment_method_url)
        self.assertEqual(response.data['valid_until'][:-1], valid_until.isoformat())
        self.assertEqual(response.data['can_be_consumed'], True)
        self.assertEqual(response.data['amount'], '200.00')
        self.assertEqual(response.data['invoice'], invoice_url)
        self.assertEqual(response.data['proforma'], proforma_url)
        self.assertEqual(response.data['currency'], currency)
        self.assertEqual(response.data['success_url'], data['success_url'])
        self.assertEqual(response.data['failed_url'], data['failed_url'])

        self.assertTrue(Transaction.objects.filter(uuid=response.data['id']))

    def test_add_transaction_without_documents(self):
        customer = CustomerFactory.create()
        payment_method = PaymentMethodFactory.create(customer=customer)
        valid_until = datetime.now()
        url = reverse('payment-method-transaction-list',
                      kwargs={'customer_pk': customer.pk, 'payment_method_id': payment_method.pk})
        data = {
            'payment_method': reverse('payment-method-detail', kwargs={'customer_pk': customer.pk,
                                                                       'payment_method_id': payment_method.id}),
            'valid_until': valid_until,
            'amount': 200.0,
        }

        response = self.client.post(url, format='json', data=data)

        expected_data = {
            'non_field_errors': [u'The transaction must have at '
                                 u'least one document (invoice or proforma).']
        }
        self.assertEqual(response.data, expected_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_transaction_with_draft_document(self):
        customer = CustomerFactory.create()
        payment_method = PaymentMethodFactory.create(customer=customer)
        proforma = ProformaFactory.create(customer=customer)
        proforma_url = reverse('proforma-detail', args=[proforma.pk])
        valid_until = datetime.now()
        url = reverse('payment-method-transaction-list',
                      kwargs={'customer_pk': customer.pk, 'payment_method_id': payment_method.pk})
        data = {
            'payment_method': reverse('payment-method-detail', kwargs={'customer_pk': customer.pk,
                                                                       'payment_method_id': payment_method.pk}),
            'valid_until': valid_until,
            'amount': 200.0,
            'proforma': proforma_url
        }

        response = self.client.post(url, format='json', data=data)

        expected_data = {
            'non_field_errors': [u'The transaction must have a non-draft document '
                                 u'(invoice or proforma).']
        }
        self.assertEqual(response.data, expected_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_transaction_with_unrelated_documents(self):
        customer = CustomerFactory.create()
        payment_method = PaymentMethodFactory.create(customer=customer)

        invoice = InvoiceFactory.create(customer=customer)
        invoice.issue()
        invoice.save()

        proforma = ProformaFactory.create(customer=customer)
        proforma.issue()
        proforma.save()

        valid_until = datetime.now()
        url = reverse('payment-method-transaction-list',
                      kwargs={'customer_pk': customer.pk, 'payment_method_id': payment_method.pk})
        invoice_url = reverse('invoice-detail', args=[invoice.pk])
        proforma_url = reverse('proforma-detail', args=[proforma.pk])
        data = {
            'payment_method': reverse('payment-method-detail', kwargs={'customer_pk': customer.pk,
                                                                       'payment_method_id': payment_method.id}),
            'valid_until': valid_until,
            'amount': 200.0,
            'invoice': invoice_url,
            'proforma': proforma_url
        }

        response = self.client.post(url, format='json', data=data)

        expected_data = {
            'non_field_errors': [u'Invoice and proforma are not related.']
        }
        self.assertEqual(response.data, expected_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_transaction_with_documents_for_a_different_customer(self):
        customer = CustomerFactory.create()
        payment_method = PaymentMethodFactory.create(customer=customer)

        proforma = ProformaFactory.create()
        proforma.state = proforma.STATES.ISSUED
        proforma.create_invoice()
        proforma.refresh_from_db()
        invoice = proforma.invoice

        valid_until = datetime.now()
        url = reverse('payment-method-transaction-list',
                      kwargs={'customer_pk': customer.pk, 'payment_method_id': payment_method.pk})
        invoice_url = reverse('invoice-detail', args=[invoice.pk])
        proforma_url = reverse('proforma-detail', args=[proforma.pk])
        data = {
            'payment_method': reverse('payment-method-detail', kwargs={'customer_pk': customer.pk,
                                                                       'payment_method_id': payment_method.id}),
            'valid_until': valid_until,
            'amount': 200.0,
            'invoice': invoice_url,
            'proforma': proforma_url
        }

        response = self.client.post(url, format='json', data=data)

        expected_data = {
            'non_field_errors': [u"Customer doesn't match with the one in documents."]
        }
        self.assertEqual(response.data, expected_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @register_processor(SomeProcessor, display_name='SomeProcessor')
    def test_patch_transaction_with_initial_status(self):
        payment_method = PaymentMethodFactory.create(
            payment_processor='someprocessor'
        )

        transaction = TransactionFactory.create(payment_method=payment_method)

        url = reverse('transaction-detail', args=[transaction.customer.pk,
                                                  transaction.uuid])

        valid_until = timezone.now()
        currency_rate_date = timezone.now().date()

        data = {
            'valid_until': valid_until,
            'currency': 'RON',
            'currency_rate_date': currency_rate_date,
            'amount': 200
        }

        response = self.client.patch(url, format='json', data=data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        transaction.refresh_from_db()
        self.assertEqual(transaction.valid_until, valid_until)
        self.assertEqual(transaction.currency, 'RON')
        self.assertEqual(transaction.currency_rate_date, currency_rate_date)
        self.assertEqual(transaction.amount, 200)

    @register_processor(SomeProcessor, display_name='SomeProcessor')
    def test_patch_transaction_documents(self):
        payment_method = PaymentMethodFactory.create(
            payment_processor='someprocessor'
        )
        transaction = TransactionFactory.create(payment_method=payment_method)
        proforma = ProformaFactory.create()
        invoice = InvoiceFactory.create(proforma=proforma)
        proforma.invoice = invoice
        proforma.save()

        invoice_url = reverse('invoice-detail', args=[invoice.pk])
        proforma_url = reverse('proforma-detail', args=[proforma.pk])
        url = reverse('transaction-detail', args=[transaction.customer.pk,
                                                  transaction.uuid])

        data = {
            'proforma': proforma_url,
            'invoice': invoice_url
        }

        response = self.client.patch(url, format='json', data=data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(response.data, {
            'proforma': [u'This field may not be modified.'],
            'invoice': [u'This field may not be modified.']
        })

    @register_processor(SomeProcessor, display_name='SomeProcessor')
    def test_patch_after_initial_state(self):
        transaction = TransactionFactory.create(state=Transaction.States.Pending)

        data = {
            'valid_until': timezone.now()
        }

        url = reverse('transaction-detail', args=[transaction.customer.pk,
                                                  transaction.uuid])

        response = self.client.patch(url, format='json', data=data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(response.data, {
            u'non_field_errors': [
                u'The transaction cannot be modified once it is in pending state.'
            ]
        })

    def test_not_allowed_methods(self):
        customer = CustomerFactory.create()
        payment_method = PaymentMethodFactory.create(customer=customer)
        transaction_1 = TransactionFactory.create(payment_method=payment_method)
        valid_until = datetime.now()
        url = reverse('transaction-detail',
                      kwargs={'customer_pk': customer.id,
                              'transaction_uuid': transaction_1.uuid})
        data = {
            'valid_until': valid_until
        }

        response = self.client.put(url, format='json', data=data)
        self.assertEqual(response.data['detail'], 'Method "PUT" not allowed.')

        response = self.client.post(url, format='json', data=data)
        self.assertEqual(response.data['detail'], 'Method "POST" not allowed.')

    def test_create_one_without_required_fields(self):
        customer = CustomerFactory.create()
        payment_method = PaymentMethodFactory.create(customer=customer)
        valid_until = datetime.now()

        data = {
            'valid_until': valid_until
        }

        url = reverse('payment-method-transaction-list',
                      kwargs={'customer_pk': customer.id,
                              'payment_method_id': payment_method.id})

        response = self.client.post(url, format='json', data=data)

        self.assertEqual(response.data['payment_method'],
                         ['This field is required.'])

    @register_processor(SomeProcessor, display_name='SomeProcessor')
    def test_filter_payment_method(self):
        customer = CustomerFactory.create()
        payment_method = PaymentMethodFactory.create(
            payment_processor='someprocessor',
            customer=customer)

        transaction1 = TransactionFactory.create(
            payment_method=payment_method
        )
        transaction_data_1 = self._transaction_data(transaction1)

        transaction2 = TransactionFactory.create(
            payment_method=payment_method
        )
        transaction_data_2 = self._transaction_data(transaction2)

        urls = [
            reverse(
                'payment-method-transaction-list', kwargs={
                    'customer_pk': customer.pk,
                    'payment_method_id': payment_method.pk}),
            reverse(
                'transaction-list', kwargs={'customer_pk': customer.pk})]

        for url in urls:
            url_method_someprocessor = url + '?payment_processor=someprocessor'
            url_no_output = url + '?payment_processor=Random'

            response = self.client.get(url_method_someprocessor, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data[0], transaction_data_1)
            self.assertEqual(response.data[1], transaction_data_2)

            response = self.client.get(url_no_output, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data, [])

    @register_processor(SomeProcessor, display_name='SomeProcessor')
    def test_filter_min_max_amount(self):
        customer = CustomerFactory.create()
        payment_method_ok = PaymentMethodFactory.create(
            payment_processor='someprocessor',
            customer=customer)

        transaction = TransactionFactory.create(
            payment_method=payment_method_ok,
            amount=100
        )
        transaction_data = self._transaction_data(transaction)

        urls = [
            reverse(
                'payment-method-transaction-list', kwargs={
                    'customer_pk': customer.pk,
                    'payment_method_id': payment_method_ok.pk}),
            reverse(
                'transaction-list', kwargs={'customer_pk': customer.pk})]

        for url in urls:
            url_with_filterable_data = url + '?min_amount=10'
            url_no_output = url + '?min_amount=150'

            response = self.client.get(url_with_filterable_data, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data[0], transaction_data)

            response = self.client.get(url_no_output, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data, [])

            url_with_filterable_data = url + '?max_amount=1050'
            url_no_output = url + '?max_amount=10'

            response = self.client.get(url_with_filterable_data, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data[0], transaction_data)

            response = self.client.get(url_no_output, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data, [])

    def _transaction_data(self, transaction):
        payment_method = transaction.payment_method
        customer = transaction.customer
        provider = transaction.provider
        proforma = transaction.proforma
        invoice = transaction.invoice

        return OrderedDict([
            ('id', unicode(transaction.uuid)),
            ('url', reverse('transaction-detail',
                            kwargs={'customer_pk': customer.id, 'transaction_uuid': transaction.uuid})),
            ('customer', reverse('customer-detail', args=[customer.pk])),
            ('provider', reverse('provider-detail', args=[provider.pk])),
            ('amount', unicode(Decimal('0.00') + transaction.amount)),
            ('currency', unicode(transaction.currency)),
            ('currency_rate_date', None),
            ('state', unicode(transaction.state)),
            ('proforma', reverse('proforma-detail', args=[proforma.pk])),
            ('invoice', reverse('invoice-detail', args=[invoice.pk])),
            ('can_be_consumed', transaction.can_be_consumed),
            ('payment_processor', reverse('payment-processor-detail', args=[payment_method.payment_processor])),
            ('payment_method', reverse('payment-method-detail', kwargs={'customer_pk': customer.id,
                                                                        'payment_method_id': payment_method.id})),
            ('pay_url', reverse('pay-transaction', kwargs={'transaction_uuid': transaction.uuid})),
            ('valid_until', None),
            ('success_url', transaction.success_url),
            ('failed_url', transaction.failed_url)
        ])
