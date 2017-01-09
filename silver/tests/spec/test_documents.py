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

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from silver.tests.factories import ProformaFactory, AdminUserFactory, \
    InvoiceFactory


class TestDocumentEndpoints(APITestCase):
    def setUp(self):
        admin_user = AdminUserFactory.create()
        self.client.force_authenticate(user=admin_user)

    def _get_expected_data(self, document):
        kind = unicode(document.kind.lower())
        return {
            u'id': document.pk,
            u'url': u'http://testserver/%ss/%s/' % (kind, document.pk),
            u'kind': kind,
            u'series': document.series,
            u'number': document.number,
            u'provider': u'http://testserver/providers/%s/' % document.provider.pk,
            u'customer': u'http://testserver/customers/%s/' % document.customer.pk,
            u'due_date': document.due_date,
            u'issue_date': document.issue_date,
            u'paid_date': document.paid_date,
            u'cancel_date': document.cancel_date,
            u'sales_tax_name': document.sales_tax_name,
            u'sales_tax_percent': u'%.2f' % document.sales_tax_percent,
            u'currency': document.currency,
            u'state': document.state,
            u'total': document.total,
            u'pdf_url': None
        }

    def test_documents_list_case_1(self):
        """
            One proforma, one invoice, without related documents
        """
        proforma = ProformaFactory.create()
        invoice = InvoiceFactory.create()

        url = reverse('document-list')
        response = self.client.get(url)

        # ^ there's a bug where specifying format='json' doesn't work
        response_data = json.loads(json.dumps(response.data))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_data), 2)

        self.assertIn(self._get_expected_data(invoice), response_data)

        self.assertIn(self._get_expected_data(proforma), response_data)

    def test_documents_list_case_2(self):
        """
            One proforma with a related invoice, one invoice
        """
        proforma = ProformaFactory.create()
        invoice1 = InvoiceFactory.create(proforma=proforma)
        proforma.invoice = invoice1
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
