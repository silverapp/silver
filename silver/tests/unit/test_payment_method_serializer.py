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
from collections import OrderedDict

from django.test import TestCase

from rest_framework.renderers import JSONRenderer
from rest_framework.test import APIRequestFactory
from rest_framework.reverse import reverse

from silver.api.serializers import PaymentMethodSerializer
from silver.tests.factories import PaymentMethodFactory


class TestPaymentMethodSerializer(TestCase):
    def test_encoding(self):
        payment_method = PaymentMethodFactory.create()

        factory = APIRequestFactory()
        url = reverse('payment-method-detail',
                      kwargs={'payment_method_id': payment_method.pk,
                              'customer_pk': payment_method.customer.pk})
        request = factory.get(url, format='json')

        serializer = PaymentMethodSerializer(payment_method, context={
            'request': request
        })

        expected_data = OrderedDict([
            ('url', 'http://testserver/customers/{}/payment_methods/{}/'.format(payment_method.customer.pk,
                                                                                payment_method.pk)),
            ('transactions', None),
            ('customer', 'http://testserver/customers/{}/'.format(payment_method.customer.pk)),
            ('payment_processor', 'http://testserver/payment_processors/Manual/'),
            ('added_at', payment_method.added_at),
            ('verified_at', None),
            ('state', 'uninitialized')
        ])

        json = JSONRenderer().render(serializer.data)
        self.assertEqual(json, JSONRenderer().render(expected_data))
