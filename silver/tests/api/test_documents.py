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

import json

from mock import patch
from freezegun import freeze_time

from django.test import override_settings

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from silver.tests.factories import (ProformaFactory, AdminUserFactory,
                                    InvoiceFactory, TransactionFactory,
                                    PaymentMethodFactory, DocumentEntryFactory)
from silver.tests.fixtures import PAYMENT_PROCESSORS
from silver.tests.utils import build_absolute_test_url

FREEZED_TIME = '2017-01-24T12:46:07Z'


@override_settings(PAYMENT_PROCESSORS=PAYMENT_PROCESSORS)
@freeze_time(FREEZED_TIME)
class TestDocumentEndpoints(APITestCase):
    def setUp(self):
        admin_user = AdminUserFactory.create()
        self.client.force_authenticate(user=admin_user)

    def _get_expected_data(self, document, transactions=None):
        kind = document.kind.lower()
        transactions = [{
            u'id': u'%s' % transaction.uuid,
            u'url': build_absolute_test_url(reverse('transaction-detail',
                                                    [transaction.customer.pk, transaction.uuid])),
            u'customer': build_absolute_test_url(reverse('customer-detail',
                                                         [transaction.customer.id])),
            u'provider': build_absolute_test_url(reverse('provider-detail',
                                                         [transaction.provider.id])),
            u'invoice': build_absolute_test_url(reverse('invoice-detail',
                                                        [transaction.invoice.id])),
            u'proforma': build_absolute_test_url(reverse('proforma-detail',
                                                         [transaction.proforma.id])),
            u'payment_processor': transaction.payment_processor,
            u'refund_code': transaction.refund_code,
            u'fail_code': transaction.fail_code,
            u'cancel_code': transaction.cancel_code,
            u'can_be_consumed': transaction.can_be_consumed,
            u'created_at': FREEZED_TIME,
            u'state': transaction.state,
            u'valid_until': transaction.valid_until,
            u'updated_at': FREEZED_TIME,
            u'currency': u'%s' % transaction.currency,
            u'amount': u'%.2f' % transaction.amount,
            u'payment_method': build_absolute_test_url(reverse('payment-method-detail',
                                                       [transaction.customer.pk,
                                                        transaction.payment_method.pk])),
            u'pay_url': build_absolute_test_url(reverse('payment', ['token']))
        } for transaction in transactions or []]

        return {
            u'id': document.pk,
            u'url':  build_absolute_test_url(reverse(kind + '-detail', [document.pk])),
            u'kind': kind,
            u'series': document.series,
            u'number': document.number,
            u'provider': build_absolute_test_url(reverse('provider-detail',
                                                         [document.provider.id])),
            u'customer': build_absolute_test_url(reverse('customer-detail',
                                                         [document.customer.id])),
            u'due_date': str(document.due_date) if document.due_date else None,
            u'issue_date': str(document.issue_date) if document.issue_date else None,
            u'paid_date': document.paid_date,
            u'cancel_date': document.cancel_date,
            u'sales_tax_name': document.sales_tax_name,
            u'sales_tax_percent': u'%.2f' % document.sales_tax_percent,
            u'currency': document.currency,
            u'transaction_currency': document.transaction_currency,
            u'state': document.state,
            u'total': document.total,
            u'pdf_url': build_absolute_test_url(document.pdf.url) if (document.pdf and
                                                                      document.pdf.url) else None,
            u'transactions': transactions,
            u'total_in_transaction_currency': document.total_in_transaction_currency
        }

    def _jwt_token(self, *args, **kwargs):
        return 'token'

    def test_documents_list_case_1(self):
        """
            One proforma, one invoice, without related documents
        """
        proforma = ProformaFactory.create()
        invoice_entries = DocumentEntryFactory.create_batch(3)
        invoice = InvoiceFactory.create(invoice_entries=invoice_entries)
        invoice.issue()
        payment_method = PaymentMethodFactory.create(customer=invoice.customer)
        transaction = TransactionFactory.create(payment_method=payment_method,
                                                invoice=invoice)

        url = reverse('document-list')

        with patch('silver.utils.payments._get_jwt_token',
                   new=self._jwt_token):
            response = self.client.get(url)

        # ^ there's a bug where specifying format='json' doesn't work
        response_data = response.data

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_data), 2)

        self.assertIn(self._get_expected_data(invoice, [transaction]),
                      response_data)

        self.assertIn(self._get_expected_data(proforma), response_data)

    def test_documents_list_case_2(self):
        """
            One proforma with a related invoice, one invoice
        """
        proforma = ProformaFactory.create()
        invoice1 = InvoiceFactory.create(related_document=proforma)
        proforma.related_document = invoice1
        proforma.save()

        invoice2 = InvoiceFactory.create()

        url = reverse('document-list')
        response = self.client.get(url)

        # ^ there's a bug where specifying format='json' doesn't work
        response_data = json.loads(json.dumps(response.data))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_data), 2)

        self.assertIn(self._get_expected_data(invoice1), response_data)

        self.assertIn(self._get_expected_data(invoice2), response_data)
