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

from django.test import override_settings
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from silver.tests.factories import AdminUserFactory
from silver.tests.fixtures import PAYMENT_PROCESSORS


@override_settings(PAYMENT_PROCESSORS=PAYMENT_PROCESSORS)
class TestPaymentProcessorsEndpoints(APITestCase):
    def setUp(self):
        admin_user = AdminUserFactory.create()
        self.client.force_authenticate(user=admin_user)

    def test_payment_processors_list(self):
        url = reverse('payment-processor-list')
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(
            {
                "name": "triggered",
                "type": "triggered",
                "allowed_currencies": ['RON', 'USD'],
                "url": "http://testserver/payment_processors/triggered/"
            },
            response.data
        )
        self.assertIn(
            {
                "name": "manual",
                "type": "manual",
                "allowed_currencies": [],
                "url": "http://testserver/payment_processors/manual/"
            },
            response.data
        )

    def test_payment_processors_detail(self):
        url = reverse('payment-processor-detail', kwargs={
            'processor_name': 'manual'
        })
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {
            'name': u'manual',
            'type': u'manual',
            'allowed_currencies': [],
            'url': 'http://testserver/payment_processors/manual/',
        })

    def test_payment_processors_detail_not_found(self):
        url = reverse('payment-processor-detail', kwargs={
            'processor_name': 'unexisting'
        })
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data, {"detail": "Not found."})
