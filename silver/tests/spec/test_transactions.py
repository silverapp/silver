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

from mock import patch

from django.utils import timezone
from django.test import override_settings
from rest_framework import status
from rest_framework.reverse import reverse as _reverse
from rest_framework.test import APITestCase

from silver.models import Proforma

from silver.models import Transaction
from silver.utils.payments import get_payment_url

from silver.tests.factories import (AdminUserFactory, TransactionFactory,
                                    PaymentMethodFactory, InvoiceFactory,
                                    ProformaFactory, CustomerFactory,
                                    DocumentEntryFactory)
from silver.tests.fixtures import (TriggeredProcessor, PAYMENT_PROCESSORS,
                                   triggered_processor)


def reverse(*args, **kwargs):
    return u'http://testserver' + _reverse(*args, **kwargs)


@override_settings(PAYMENT_PROCESSORS=PAYMENT_PROCESSORS)
class TestTransactionEndpoint(APITestCase):
    def setUp(self):
        self.user = AdminUserFactory.create()
        self.client.force_authenticate(user=self.user)

    def test_get_transaction(self):
        customer = CustomerFactory.create()
        payment_method = PaymentMethodFactory.create(customer=customer)

        transaction = TransactionFactory.create(payment_method=payment_method)
        expected = self._transaction_data(transaction)

        with patch('silver.utils.payments._get_jwt_token') as mocked_token:
            mocked_token.return_value = 'token'

            url = reverse('transaction-detail',
                          kwargs={'customer_pk': customer.pk,
                                  'transaction_uuid': transaction.uuid})
            response = self.client.get(url, format='json')

            self.assertEqual(response.data, dict(expected))

    def test_list_transactions(self):
        customer = CustomerFactory.create()
        payment_method = PaymentMethodFactory.create(customer=customer)

        transaction_1 = TransactionFactory.create(payment_method=payment_method)
        expected_t1 = self._transaction_data(transaction_1)
        transaction_2 = TransactionFactory.create(payment_method=payment_method)
        expected_t2 = self._transaction_data(transaction_2)

        with patch('silver.utils.payments._get_jwt_token') as mocked_token:
            mocked_token.return_value = 'token'

            url = reverse('transaction-list',
                          kwargs={'customer_pk': customer.pk})

            response = self.client.get(url, format='json')

            self.assertEqual(response.data[0], expected_t1)
            self.assertEqual(response.data[1], expected_t2)

    def test_add_transaction(self):
        customer = CustomerFactory.create()
        payment_method = PaymentMethodFactory.create(customer=customer)

        entry = DocumentEntryFactory(quantity=1, unit_price=200)
        proforma = ProformaFactory.create(customer=customer,
                                          proforma_entries=[entry])
        proforma.issue()
        proforma.create_invoice()
        proforma.refresh_from_db()
        invoice = proforma.invoice

        payment_method_url = reverse('payment-method-detail',
                                     kwargs={'customer_pk': customer.pk,
                                             'payment_method_id': payment_method.id})

        invoice_url = reverse('invoice-detail', args=[invoice.pk])
        proforma_url = reverse('proforma-detail', args=[proforma.pk])

        url = reverse('payment-method-transaction-list',
                      kwargs={'customer_pk': customer.pk,
                              'payment_method_id': payment_method.pk})

        valid_until = datetime.now().replace(microsecond=0) + timedelta(minutes=30)

        currency = invoice.transaction_currency

        data = {
            'payment_method': reverse('payment-method-detail',
                                      kwargs={'customer_pk': customer.pk,
                                              'payment_method_id': payment_method.id}),
            'amount': invoice.total_in_transaction_currency,
            'invoice': invoice_url,
            'proforma': proforma_url,
            'valid_until': valid_until,
            'currency': currency,
        }

        response = self.client.post(url, format='json', data=data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(response.data['payment_method'], payment_method_url)
        self.assertEqual(response.data['valid_until'][:-1], valid_until.isoformat())
        self.assertEqual(response.data['can_be_consumed'], True)
        self.assertEqual(response.data['amount'],
                         unicode(invoice.total_in_transaction_currency))
        self.assertEqual(response.data['invoice'], invoice_url)
        self.assertEqual(response.data['proforma'], proforma_url)
        self.assertEqual(response.data['currency'], currency)

        self.assertTrue(Transaction.objects.filter(uuid=response.data['id']))

    def test_add_transaction_without_documents(self):
        customer = CustomerFactory.create()
        payment_method = PaymentMethodFactory.create(customer=customer)
        valid_until = datetime.now().replace(microsecond=0)
        url = reverse('payment-method-transaction-list',
                      kwargs={'customer_pk': customer.pk,
                              'payment_method_id': payment_method.pk})
        data = {
            'payment_method': reverse('payment-method-detail',
                                      kwargs={'customer_pk': customer.pk,
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
        valid_until = datetime.now().replace(microsecond=0)
        url = reverse('payment-method-transaction-list',
                      kwargs={'customer_pk': customer.pk,
                              'payment_method_id': payment_method.pk})
        data = {
            'payment_method': reverse('payment-method-detail',
                                      kwargs={'customer_pk': customer.pk,
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

        proforma = ProformaFactory.create(customer=customer)
        proforma.issue()

        valid_until = datetime.now().replace(microsecond=0)
        url = reverse('payment-method-transaction-list',
                      kwargs={'customer_pk': customer.pk,
                              'payment_method_id': payment_method.pk})

        invoice_url = reverse('invoice-detail', args=[invoice.pk])
        proforma_url = reverse('proforma-detail', args=[proforma.pk])
        data = {
            'payment_method': reverse('payment-method-detail',
                                      kwargs={'customer_pk': customer.pk,
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
        proforma.issue()
        proforma.create_invoice()
        proforma.refresh_from_db()
        invoice = proforma.invoice

        valid_until = datetime.now().replace(microsecond=0)
        url = reverse('payment-method-transaction-list',
                      kwargs={'customer_pk': customer.pk,
                              'payment_method_id': payment_method.pk})

        invoice_url = reverse('invoice-detail', args=[invoice.pk])
        proforma_url = reverse('proforma-detail', args=[proforma.pk])
        data = {
            'payment_method': reverse('payment-method-detail',
                                      kwargs={'customer_pk': customer.pk,
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

    def test_add_transaction_without_currency_and_amount(self):
        customer = CustomerFactory.create()
        payment_method = PaymentMethodFactory.create(customer=customer)

        entries = DocumentEntryFactory.create_batch(2)
        proforma = ProformaFactory.create(customer=customer,
                                          state=Proforma.STATES.ISSUED,
                                          issue_date=timezone.now().date(),
                                          currency='USD', transaction_currency='RON',
                                          transaction_xe_rate=Decimal('0.25'),
                                          proforma_entries=entries)
        proforma.create_invoice()
        invoice = proforma.invoice

        valid_until = datetime.now().replace(microsecond=0) + timedelta(minutes=30)
        url = reverse('payment-method-transaction-list',
                      kwargs={'customer_pk': customer.pk,
                              'payment_method_id': payment_method.pk})

        payment_method_url = reverse('payment-method-detail',
                                     kwargs={'customer_pk': customer.pk,
                                             'payment_method_id': payment_method.id})
        invoice_url = reverse('invoice-detail', args=[invoice.pk])
        proforma_url = reverse('proforma-detail', args=[proforma.pk])
        data = {
            'payment_method': reverse('payment-method-detail',
                                      kwargs={'customer_pk': customer.pk,
                                              'payment_method_id': payment_method.id}),
            'valid_until': valid_until,
            'invoice': invoice_url,
            'proforma': proforma_url
        }

        response = self.client.post(url, format='json', data=data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(response.data['payment_method'], payment_method_url)
        self.assertEqual(response.data['valid_until'][:-1], valid_until.isoformat())
        self.assertEqual(response.data['can_be_consumed'], True)
        self.assertEqual(response.data['amount'],
                         unicode(invoice.total_in_transaction_currency))
        self.assertEqual(response.data['invoice'], invoice_url)
        self.assertEqual(response.data['proforma'], proforma_url)
        self.assertEqual(response.data['currency'], invoice.transaction_currency)

    def test_add_transaction_with_currency_different_from_document(self):
        customer = CustomerFactory.create()
        payment_method = PaymentMethodFactory.create(customer=customer)

        proforma = ProformaFactory.create(customer=customer,
                                          state=Proforma.STATES.ISSUED,
                                          issue_date=timezone.now().date())
        proforma.create_invoice()
        invoice = proforma.invoice

        valid_until = datetime.now().replace(microsecond=0)
        url = reverse('payment-method-transaction-list',
                      kwargs={'customer_pk': customer.pk,
                              'payment_method_id': payment_method.pk})

        invoice_url = reverse('invoice-detail', args=[invoice.pk])
        proforma_url = reverse('proforma-detail', args=[proforma.pk])
        data = {
            'payment_method': reverse('payment-method-detail',
                                      kwargs={'customer_pk': customer.pk,
                                              'payment_method_id': payment_method.id}),
            'valid_until': valid_until,
            'currency': 'EUR',
            'amount': invoice.total_in_transaction_currency,
            'invoice': invoice_url,
            'proforma': proforma_url
        }

        response = self.client.post(url, format='json', data=data)

        expected_data = {
            'non_field_errors': [u"Transaction currency is different from it's "
                                 u"document's transaction_currency."]
        }
        self.assertEqual(response.data, expected_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_transaction_with_amount_greater_than_what_should_be_charged(self):
        customer = CustomerFactory.create()
        payment_method = PaymentMethodFactory.create(customer=customer)

        proforma = ProformaFactory.create(customer=customer,
                                          state=Proforma.STATES.ISSUED,
                                          issue_date=timezone.now().date())
        proforma.create_invoice()
        invoice = proforma.invoice

        valid_until = datetime.now().replace(microsecond=0)
        url = reverse('payment-method-transaction-list',
                      kwargs={'customer_pk': customer.pk,
                              'payment_method_id': payment_method.pk})

        invoice_url = reverse('invoice-detail', args=[invoice.pk])
        proforma_url = reverse('proforma-detail', args=[proforma.pk])
        data = {
            'payment_method': reverse('payment-method-detail',
                                      kwargs={'customer_pk': customer.pk,
                                              'payment_method_id': payment_method.id}),
            'valid_until': valid_until,
            'amount': invoice.total_in_transaction_currency + 1,
            'invoice': invoice_url,
            'proforma': proforma_url
        }

        response = self.client.post(url, format='json', data=data)

        expected_data = {
            'non_field_errors': [u"Amount is greater than the amount that should be charged in "
                                 u"order to pay the billing document."]
        }
        self.assertEqual(response.data, expected_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_transaction_with_initial_status(self):
        payment_method = PaymentMethodFactory.create(
            payment_processor=triggered_processor
        )

        transaction = TransactionFactory.create(payment_method=payment_method)

        url = reverse('transaction-detail', args=[transaction.customer.pk,
                                                  transaction.uuid])

        valid_until = timezone.now().replace(microsecond=0)

        data = {
            'valid_until': valid_until,
        }

        response = self.client.patch(url, format='json', data=data)

        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         "status %s, data %s" % (response.status_code,
                                                 response.data))

        transaction.refresh_from_db()
        self.assertEqual(transaction.valid_until, valid_until)

    def test_patch_transaction_not_allowed_fields(self):
        payment_method = PaymentMethodFactory.create(
            payment_processor=triggered_processor
        )

        transaction = TransactionFactory.create(payment_method=payment_method)

        proforma = ProformaFactory.create(state='issued')
        invoice = InvoiceFactory.create(proforma=proforma, state='issued')
        proforma.invoice = invoice
        proforma.save()

        invoice_url = reverse('invoice-detail', args=[invoice.pk])
        proforma_url = reverse('proforma-detail', args=[proforma.pk])
        url = reverse('transaction-detail', args=[transaction.customer.pk,
                                                  transaction.uuid])

        new_payment_method = PaymentMethodFactory.create(
            payment_processor=triggered_processor,
            customer=payment_method.customer
        )

        new_payment_method_url = reverse('payment-method-detail', kwargs={
            'customer_pk': new_payment_method.customer.pk,
            'payment_method_id': new_payment_method.pk
        })

        data = {
            'proforma': proforma_url,
            'invoice': invoice_url,
            'currency': 'EUR',
            'amount': 1234,
            'payment_method': new_payment_method_url
        }

        response = self.client.patch(url, format='json', data=data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(response.data, {
            'proforma': [u'This field may not be modified.'],
            'invoice': [u'This field may not be modified.'],
            'currency': [u'This field may not be modified.'],
            'amount': [u'This field may not be modified.'],
            'payment_method': [u'This field may not be modified.']
        })

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
        valid_until = datetime.now().replace(microsecond=0)
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
        valid_until = datetime.now().replace(microsecond=0)

        data = {
            'valid_until': valid_until
        }

        url = reverse('payment-method-transaction-list',
                      kwargs={'customer_pk': customer.id,
                              'payment_method_id': payment_method.id})

        response = self.client.post(url, format='json', data=data)

        self.assertEqual(response.data['payment_method'],
                         ['This field is required.'])

    def test_filter_payment_method(self):
        customer = CustomerFactory.create()
        payment_method = PaymentMethodFactory.create(
            payment_processor=triggered_processor,
            customer=customer
        )

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
            url_method_someprocessor = (
                url + '?payment_processor=' + triggered_processor
            )

            url_no_output = url + '?payment_processor=Random'

            with patch('silver.utils.payments._get_jwt_token') as mocked_token:
                mocked_token.return_value = 'token'

                response = self.client.get(url_method_someprocessor, format='json')
                self.assertEqual(response.status_code, status.HTTP_200_OK)

                transaction1.refresh_from_db()
                transaction_data_1['updated_at'] = response.data[0]['updated_at']

                transaction1.refresh_from_db()
                transaction_data_2['updated_at'] = response.data[1]['updated_at']

                self.assertEqual(response.data[0], transaction_data_1)
                self.assertEqual(response.data[1], transaction_data_2)

                response = self.client.get(url_no_output, format='json')
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data, [])

    def test_filter_min_max_amount(self):
        payment_method = PaymentMethodFactory.create(
            payment_processor=triggered_processor,
        )
        customer = payment_method.customer

        entry = DocumentEntryFactory(quantity=1, unit_price=100)
        invoice = InvoiceFactory.create(invoice_entries=[entry],
                                        customer=customer)
        invoice.issue()

        transaction = TransactionFactory.create(
            payment_method=payment_method,
            invoice=invoice
        )

        transaction_data = self._transaction_data(transaction)

        urls = [
            reverse(
                'payment-method-transaction-list', kwargs={
                    'customer_pk': customer.pk,
                    'payment_method_id': payment_method.pk}),
            reverse(
                'transaction-list', kwargs={'customer_pk': customer.pk})]

        for url in urls:
            url_with_filterable_data = url + '?min_amount=10'
            url_no_output = url + '?min_amount=150'

            with patch('silver.utils.payments._get_jwt_token') as mocked_token:
                mocked_token.return_value = 'token'

                response = self.client.get(url_with_filterable_data, format='json')

                transaction.refresh_from_db()
                transaction_data['updated_at'] = response.data[0]['updated_at']

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data[0], transaction_data)

                response = self.client.get(url_no_output, format='json')
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data, [])

                url_with_filterable_data = url + '?max_amount=1050'
                url_no_output = url + '?max_amount=10'

                response = self.client.get(url_with_filterable_data, format='json')

                transaction.refresh_from_db()
                transaction_data['updated_at'] = response.data[0]['updated_at']

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data[0], transaction_data)

                response = self.client.get(url_no_output, format='json')
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data, [])

    def test_cancel_action(self):
        transaction_initial = TransactionFactory.create(state='initial')
        transaction_pending = TransactionFactory.create(state='pending')

        for transaction in [transaction_initial, transaction_pending]:
            url = reverse('transaction-action', kwargs={
                'customer_pk': transaction.payment_method.customer.pk,
                'transaction_uuid': str(transaction.uuid),
                'requested_action': 'cancel',
            })

            response = self.client.post(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            transaction.refresh_from_db()
            self.assertEqual(transaction.state,
                             Transaction.States.Canceled)

    def test_invalid_transaction_action(self):
        transaction = TransactionFactory.create(state='settled')

        url = reverse('transaction-action', kwargs={
            'customer_pk': transaction.payment_method.customer.pk,
            'transaction_uuid': str(transaction.uuid),
            'requested_action': 'cancel',
        })

        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        expected_error = "Can't execute action because the transaction is in "\
                         "an incorrect state: settled"
        self.assertEqual(response.data, {'errors': expected_error})

    def _transaction_data(self, transaction):
        transaction.refresh_from_db()

        payment_method = transaction.payment_method
        customer = transaction.customer
        provider = transaction.provider
        proforma = transaction.proforma
        invoice = transaction.invoice

        with patch('silver.utils.payments._get_jwt_token') as mocked_token:
            mocked_token.return_value = 'token'

            return OrderedDict([
                ('id', unicode(transaction.uuid)),
                ('url', reverse('transaction-detail',
                                kwargs={'customer_pk': customer.id,
                                        'transaction_uuid': transaction.uuid})),
                ('customer', reverse('customer-detail', args=[customer.pk])),
                ('provider', reverse('provider-detail', args=[provider.pk])),
                ('amount', unicode(Decimal('0.00') + transaction.amount)),
                ('currency', unicode(transaction.currency)),
                ('state', unicode(transaction.state)),
                ('proforma', reverse('proforma-detail', args=[proforma.pk])),
                ('invoice', reverse('invoice-detail', args=[invoice.pk])),
                ('can_be_consumed', transaction.can_be_consumed),
                ('payment_processor', payment_method.payment_processor),
                ('payment_method', reverse('payment-method-detail',
                                           kwargs={'customer_pk': customer.id,
                                                   'payment_method_id': payment_method.id})),
                ('pay_url', 'http://testserver' + get_payment_url(transaction, None)),
                ('valid_until', None),

                ('updated_at', transaction.updated_at.isoformat()[:-6] + 'Z'),
                ('created_at', transaction.created_at.isoformat()[:-6] + 'Z'),
                ('fail_code', transaction.fail_code),
                ('refund_code', transaction.refund_code),
                ('cancel_code', transaction.cancel_code)
            ])
