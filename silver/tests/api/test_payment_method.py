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

from __future__ import absolute_import

import sys

from copy import deepcopy

from django.test import override_settings

from rest_framework import permissions, status
from rest_framework.reverse import reverse

from silver.api.serializers.payment_methods_serializers import PaymentMethodSerializer
from silver.api.views.payment_method_views import PaymentMethodList, PaymentMethodDetail
from silver.models import PaymentMethod, Transaction
from silver.tests.factories import (CustomerFactory, PaymentMethodFactory,
                                    TransactionFactory)
from silver.tests.fixtures import (PAYMENT_PROCESSORS, manual_processor,
                                   triggered_processor, failing_void_processor)
from silver.tests.api.utils.api_get_assert import APIGetAssert


@override_settings(PAYMENT_PROCESSORS=PAYMENT_PROCESSORS)
class TestPaymentMethodEndpoints(APIGetAssert):
    serializer_class = PaymentMethodSerializer

    def setUp(self):
        self.customer = CustomerFactory.create()
        super(TestPaymentMethodEndpoints, self).setUp()

    def create_payment_method(self, *args, **kwargs):
        payment_method = PaymentMethodFactory.create(*args, **kwargs)
        payment_method.added_at.replace(microsecond=0)

        return payment_method

    def test_get_listing(self):
        PaymentMethodFactory.create(customer=CustomerFactory.create())
        payment_method = self.create_payment_method(customer=self.customer)

        url = reverse('payment-method-list', kwargs={
            'customer_pk': self.customer.pk
        })

        self.assert_get_data(url, [payment_method])

    def test_get_detail(self):
        PaymentMethodFactory.create(customer=CustomerFactory.create())
        payment_method = self.create_payment_method(customer=self.customer)

        url = reverse('payment-method-detail', kwargs={
            'customer_pk': self.customer.pk,
            'payment_method_id': payment_method.pk
        })

        self.assert_get_data(url, payment_method)

    def test_post_listing(self):
        url = reverse('payment-method-list', kwargs={
            'customer_pk': self.customer.pk
        })

        response = self.client.post(url, data={
            'payment_processor_name': manual_processor
        }, format='json')

        payment_method = PaymentMethod.objects.get(customer=self.customer)
        self.assert_get_data(response.data['url'], payment_method)

    def test_put_detail_ignore_customer_change(self):
        other_customer = CustomerFactory.create()
        payment_method = self.create_payment_method(customer=self.customer)

        url = reverse('payment-method-detail', kwargs={
            'customer_pk': self.customer.pk,
            'payment_method_id': payment_method.pk
        })
        response = self.client.get(url, format='json')

        expected_data = deepcopy(response.data)
        data = response.data
        data['customer'] = reverse('customer-detail',
                                   request=response.wsgi_request,
                                   kwargs={'customer_pk': other_customer.pk})

        response = self.client.put(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, expected_data)

    def test_put_detail_cannot_change_processor(self):
        payment_method = self.create_payment_method(customer=self.customer)

        url = reverse('payment-method-detail', kwargs={
            'customer_pk': self.customer.pk,
            'payment_method_id': payment_method.pk
        })
        response = self.client.get(url, format='json')

        data = response.data
        data['payment_processor_name'] = triggered_processor

        response = self.client.put(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {
            'payment_processor_name': [u'This field may not be modified.']
        })

    def test_put_detail_reenable_payment_method(self):
        """
            payment_method.canceled from True to False
        """

        payment_method = self.create_payment_method(customer=self.customer,
                                                    canceled=True)

        url = reverse('payment-method-detail', kwargs={
            'customer_pk': self.customer.pk,
            'payment_method_id': payment_method.pk
        })

        response = self.client.get(url, format='json')
        data = response.data
        data['canceled'] = False

        response = self.client.put(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {
            'non_field_errors': [u'You cannot update a canceled payment method.']
        })

    def test_put_detail_unverify_payment_method(self):
        """
            payment_method.canceled from True to False
        """

        payment_method = self.create_payment_method(customer=self.customer,
                                                    verified=True)

        url = reverse('payment-method-detail', kwargs={
            'customer_pk': self.customer.pk,
            'payment_method_id': payment_method.pk
        })

        response = self.client.get(url, format='json')
        data = response.data
        data['verified'] = False

        response = self.client.put(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {
            'verified': [u'You cannot unverify a payment method.']
        })

    def test_put_detail(self):
        payment_method = self.create_payment_method(customer=self.customer,
                                                    canceled=False,
                                                    verified=False)

        url = reverse('payment-method-detail', kwargs={
            'customer_pk': self.customer.pk,
            'payment_method_id': payment_method.pk
        })

        response = self.client.get(url, format='json')
        data = response.data
        data['canceled'] = True
        data['verified'] = True

        response = self.client.put(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, data)

    def test_get_listing_no_customer(self):
        url = reverse('payment-method-list', kwargs={
            'customer_pk': sys.maxsize
        })

        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data, {'detail': 'Not found.'})

    def test_get_detail_no_customer(self):
        url = reverse('payment-method-detail', kwargs={
            'customer_pk': sys.maxsize,
            'payment_method_id': 0
        })

        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data, {'detail': 'Not found.'})

    def test_get_detail_no_payment_method(self):
        url = reverse('payment-method-detail', kwargs={
            'customer_pk': self.customer.pk,
            'payment_method_id': sys.maxsize
        })

        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data, {'detail': 'Not found.'})

    def test_post_listing_no_customer(self):
        url = reverse('payment-method-list', kwargs={
            'customer_pk': sys.maxsize
        })

        response = self.client.post(url, data={
            'payment_processor_name': manual_processor,
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data, {'detail': 'Not found.'})

    def test_post_listing_incomplete_body_1(self):
        url = reverse('payment-method-list', kwargs={
            'customer_pk': 0
        })

        response = self.client.post(url, data={}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {
            'payment_processor_name': ['This field is required.']})

    def test_permissions(self):
        self.assertEqual(PaymentMethodList.permission_classes,
                         (permissions.IsAuthenticated,))
        self.assertEqual(PaymentMethodDetail.permission_classes,
                         (permissions.IsAuthenticated,))

    def test_filter_processor(self):
        payment_method = self.create_payment_method(customer=self.customer)

        url = reverse('payment-method-list', kwargs={
            'customer_pk': self.customer.pk
        })

        url_manual_processor = url + '?processor=' + manual_processor
        url_no_output = url + '?processor=random'

        self.assert_get_data(url_manual_processor, [payment_method])
        self.assert_get_data(url_no_output, [])

    def test_filter_canceled(self):
        payment_method = self.create_payment_method(customer=self.customer)

        url = reverse('payment-method-list', kwargs={
            'customer_pk': self.customer.pk
        })

        url_manual_processor = url + '?canceled=False'
        url_no_output = url + '?canceled=True'

        self.assert_get_data(url_manual_processor, [payment_method])
        self.assert_get_data(url_no_output, [])

    def test_filter_verified(self):
        payment_method = self.create_payment_method(customer=self.customer)

        url = reverse('payment-method-list', kwargs={
            'customer_pk': self.customer.pk
        })

        url_manual_processor = url + '?verified=False'
        url_no_output = url + '?verified=True'

        self.assert_get_data(url_manual_processor, [payment_method])
        self.assert_get_data(url_no_output, [])

    def test_cancel_action(self):
        payment_method = self.create_payment_method(customer=self.customer,
                                                    payment_processor='triggered')
        transaction_initial = TransactionFactory.create(payment_method=payment_method)
        transaction_pending = TransactionFactory.create(payment_method=payment_method,
                                                        state='pending')

        url = reverse('payment-method-action', kwargs={
            'customer_pk': self.customer.pk,
            'payment_method_id': payment_method.pk,
            'requested_action': 'cancel',
        })

        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        payment_method.refresh_from_db()
        transaction_initial.refresh_from_db()
        transaction_pending.refresh_from_db()

        self.assertTrue(payment_method.canceled)
        self.assertEqual(transaction_initial.state, Transaction.States.Canceled)
        self.assertEqual(transaction_pending.state, Transaction.States.Canceled)

    @override_settings(PAYMENT_PROCESSORS=PAYMENT_PROCESSORS)
    def test_cancel_action_failed_void(self):
        payment_method = self.create_payment_method(
            customer=self.customer, payment_processor=failing_void_processor
        )

        transaction_initial = TransactionFactory.create(payment_method=payment_method)
        transaction_pending = TransactionFactory.create(payment_method=payment_method,
                                                        state='pending')

        url = reverse('payment-method-action', kwargs={
            'customer_pk': self.customer.pk,
            'payment_method_id': payment_method.pk,
            'requested_action': 'cancel',
        })

        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        expected_error = "Transaction {} couldn't be voided".format(transaction_pending.uuid)
        self.assertEqual(response.data, {'errors': [expected_error]})
