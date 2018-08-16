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

from __future__ import absolute_import

from collections import OrderedDict

from django.test import TestCase, override_settings
from django.utils import timezone

from rest_framework.renderers import JSONRenderer
from rest_framework.test import APIRequestFactory
from rest_framework.reverse import reverse

from silver.api.serializers.payment_methods_serializers import PaymentMethodSerializer
from silver.tests.factories import PaymentMethodFactory
from silver.tests.fixtures import (PAYMENT_PROCESSORS, manual_processor,
                                   ManualProcessor)
from silver.tests.utils import build_absolute_test_url


@override_settings(PAYMENT_PROCESSORS=PAYMENT_PROCESSORS)
class TestPaymentMethodSerializer(TestCase):
    def test_encoding(self):
        now = timezone.now().replace(microsecond=0)
        payment_method = PaymentMethodFactory.create(added_at=now)

        factory = APIRequestFactory()
        url = reverse('payment-method-detail',
                      kwargs={'payment_method_id': payment_method.pk,
                              'customer_pk': payment_method.customer.pk})
        request = factory.get(url, format='json')

        serializer = PaymentMethodSerializer(payment_method, context={
            'request': request
        })

        self_url = build_absolute_test_url(url)
        transactions_url = build_absolute_test_url(
            reverse('payment-method-transaction-list',
                    [payment_method.pk, payment_method.customer.pk])
        )
        customer_url = build_absolute_test_url(
            reverse('customer-detail', [payment_method.customer.pk])
        )
        expected_data = OrderedDict([
            ('url', self_url),
            ('transactions', transactions_url),
            ('customer', customer_url),
            ('payment_processor_name', manual_processor),
            ('payment_processor', OrderedDict([
                ("type", ManualProcessor.type),
                ("name", manual_processor),
                ("allowed_currencies", []),
                ("url", build_absolute_test_url(reverse('payment-processor-detail', ['manual'])))
            ])),
            ('added_at', payment_method.added_at),
            ('verified', False),
            ('canceled', False),
            ('valid_until', None),
            ('display_info', None),
        ])

        json = JSONRenderer().render(serializer.data)
        self.assertEqual(json, JSONRenderer().render(expected_data))
