import sys
from copy import deepcopy

from six import iteritems

from django.test import override_settings

from rest_framework import permissions, status
from rest_framework.reverse import reverse

from silver.models import PaymentMethod
from silver.models.payment_processors.base import PaymentProcessorBase
from silver.models.payment_processors.mixins import TriggeredProcessorMixin
from silver.api.serializers import PaymentMethodSerializer
from silver.api.views import PaymentMethodList, PaymentMethodDetail

from silver.tests.spec.util.api_get_assert import APIGetAssert
from silver.tests.factories import CustomerFactory, PaymentMethodFactory
from silver.tests.utils import register_processor


class SomeProcessor(PaymentProcessorBase, TriggeredProcessorMixin):
    reference = 'someprocessor'


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
        processor_url = reverse('payment-processor-detail', kwargs={
            'processor_name': 'manual'
        })

        url = reverse('payment-method-list', kwargs={
            'customer_pk': self.customer.pk
        })

        response = self.client.post(url, data={
            'payment_processor': processor_url,
        }, format='json')

        payment_method = PaymentMethod.objects.get(customer=self.customer)
        self.assert_get_data(response.data['url'], payment_method)

    def test_put_detail_additional_data_disabled_state(self):
        payment_method = self.create_payment_method(customer=self.customer,
                                                    enabled=False)

        url = reverse('payment-method-detail', kwargs={
            'customer_pk': self.customer.pk,
            'payment_method_id': payment_method.pk
        })
        response = self.client.get(url, format='json')

        data = response.data
        data['additional_data'] = '{"random": "value"}'

        response = self.client.put(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {
            u'non_field_errors': [u"'additional_data' must not be given after "
                                  u"the payment method has been enabled once."]
        })

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

    @register_processor(SomeProcessor, display_name='SomeProcessor')
    def test_put_detail_cannot_change_processor(self):
        payment_method = self.create_payment_method(customer=self.customer)

        url = reverse('payment-method-detail', kwargs={
            'customer_pk': self.customer.pk,
            'payment_method_id': payment_method.pk
        })
        response = self.client.get(url, format='json')

        data = response.data
        payment_processor = reverse('payment-processor-detail',
                                    kwargs={'processor_name': 'someprocessor'},
                                    request=response.wsgi_request)
        data['payment_processor'] = payment_processor

        response = self.client.put(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {
            'payment_processor': [u'This field may not be modified.']
        })

    def test_put_detail(self):
        payment_method = self.create_payment_method(customer=self.customer,
                                                    enabled=False,
                                                    verified=False)

        url = reverse('payment-method-detail', kwargs={
            'customer_pk': self.customer.pk,
            'payment_method_id': payment_method.pk
        })

        response = self.client.get(url, format='json')
        data = response.data
        data['enabled'] = True
        data['verified'] = True

        response = self.client.put(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, data)

    def test_post_listing_additional_data_unverified(self):
        processor_url = reverse('payment-processor-detail', kwargs={
            'processor_name': 'manual'
        })

        url = reverse('payment-method-list', kwargs={
            'customer_pk': self.customer.pk
        })

        response = self.client.post(url, data={
            'payment_processor': processor_url,
            'verified': False,
            'additional_data': '{"random": "value"}'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {
            'non_field_errors':
                ["If 'additional_data' is specified, then the payment "
                 "method need to be unverified."]})

    def test_get_listing_no_customer(self):
        url = reverse('payment-method-list', kwargs={
            'customer_pk': sys.maxint
        })

        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data, {'detail': 'Not found.'})

    def test_get_detail_no_customer(self):
        url = reverse('payment-method-detail', kwargs={
            'customer_pk': sys.maxint,
            'payment_method_id': 0
        })

        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data, {'detail': 'Not found.'})

    def test_get_detail_no_payment_method(self):
        url = reverse('payment-method-detail', kwargs={
            'customer_pk': self.customer.pk,
            'payment_method_id': sys.maxint
        })

        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data, {'detail': 'Not found.'})

    def test_post_listing_no_customer(self):
        processor_url = reverse('payment-processor-detail', kwargs={
            'processor_name': 'manual'
        })

        url = reverse('payment-method-list', kwargs={
            'customer_pk': sys.maxint
        })

        response = self.client.post(url, data={
            'payment_processor': processor_url,
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
            'payment_processor': ['This field is required.']})

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

        url_manual_processor = url + '?processor=manual'
        url_no_output = url + '?processor=random'

        self.assert_get_data(url_manual_processor, [payment_method])
        self.assert_get_data(url_no_output, [])

    def test_filter_enabled(self):
        payment_method = self.create_payment_method(customer=self.customer)

        url = reverse('payment-method-list', kwargs={
            'customer_pk': self.customer.pk
        })

        url_manual_processor = url + '?enabled=True'
        url_no_output = url + '?enabled=False'

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
