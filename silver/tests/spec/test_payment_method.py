import sys
from rest_framework import permissions, status
from rest_framework.reverse import reverse

from silver.api.serializers import PaymentMethodSerializer
from silver.models import PaymentMethod
from silver.api.views import PaymentMethodList, PaymentMethodDetail
from silver.tests.factories import CustomerFactory, PaymentMethodFactory
from silver.tests.spec.util.api_get_assert import APIGetAssert


class TestPaymentMethodEndpoints(APIGetAssert):
    serializer_class = PaymentMethodSerializer

    def setUp(self):
        self.customer = CustomerFactory.create()

        super(TestPaymentMethodEndpoints, self).setUp()

    def create_payment_method(self, *args, **kwargs):
        method = PaymentMethodFactory.create(*args, **kwargs)

        # mysql does not store fractional time units but the object
        # created will have them so we can't use it directly
        #  to check the output
        method.refresh_from_db()

        return method

    def test_get_listing(self):
        PaymentMethodFactory.create(customer=CustomerFactory.create())
        method = self.create_payment_method(customer=self.customer)

        url = reverse('payment-method-list', kwargs={
            'customer_pk': self.customer.pk
        })

        self.assert_get_data(url, [method])

    def test_get_detail(self):
        PaymentMethodFactory.create(customer=CustomerFactory.create())
        method = self.create_payment_method(customer=self.customer)

        url = reverse('payment-method-detail', kwargs={
            'customer_pk': self.customer.pk,
            'payment_method_id': method.pk
        })

        self.assert_get_data(url, method)

    def test_post_listing(self):
        processor_url = reverse('payment-processor-detail', kwargs={
            'processor_name': 'manual'
        })

        url = reverse('payment-method-list', kwargs={
            'customer_pk': self.customer.pk
        })

        response = self.client.post(url, data={
            'payment_processor': processor_url,
            'state': PaymentMethod.States.Uninitialized
        }, format='json')

        method = PaymentMethod.objects.get(customer=self.customer)
        self.assert_get_data(response.data['url'], method)

    def test_post_listing_additional_data_wrong_state(self):
        processor_url = reverse('payment-processor-detail', kwargs={
            'processor_name': 'manual'
        })

        url = reverse('payment-method-list', kwargs={
            'customer_pk': self.customer.pk
        })

        response = self.client.post(url, data={
            'payment_processor': processor_url,
            'state': PaymentMethod.States.Uninitialized,
            'additional_data': '{"random": "value"}'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_listing_invalid_initial_state(self):
        invalid_initial_states = list(
            set([s[0] for s in PaymentMethod.States.Choices]) -
            {PaymentMethod.States.Uninitialized,
             PaymentMethod.States.Unverified,
             PaymentMethod.States.Enabled})

        processor_url = reverse('payment-processor-detail', kwargs={
            'processor_name': 'manual'
        })

        url = reverse('payment-method-list', kwargs={
            'customer_pk': self.customer.pk
        })

        for state in invalid_initial_states:
            response = self.client.post(url, data={
                'payment_processor': processor_url,
                'state': state
            }, format='json')

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_put_detail_invalid_state_transitions(self):
        # TODO add all of them here...
        method = self.create_payment_method(customer=self.customer,
                                            state=PaymentMethod.States.Enabled)

        url = reverse('payment-method-detail', kwargs={
            'customer_pk': self.customer.pk,
            'payment_method_id': method.pk
        })
        response = self.client.get(url, format='json')

        data = response.data
        data['state'] = PaymentMethod.States.Uninitialized

        response = self.client.put(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_put_detail_additional_data_disabled_state(self):
        method = self.create_payment_method(customer=self.customer,
                                            state=PaymentMethod.States.Disabled)

        url = reverse('payment-method-detail', kwargs={
            'customer_pk': self.customer.pk,
            'payment_method_id': method.pk
        })
        response = self.client.get(url, format='json')

        data = response.data
        data['additional_data'] = '{"random":"value"}'

        response = self.client.put(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_put_detail_change_customer(self):
        # TODO fix this
        # serializer compares an url with the customer object
        other_customer = CustomerFactory.create()
        method = self.create_payment_method(customer=self.customer)

        url = reverse('payment-method-detail', kwargs={
            'customer_pk': self.customer.pk,
            'payment_method_id': method.pk
        })
        response = self.client.get(url, format='json')

        data = response.data
        data['customer'] = reverse('customer-detail',
                                   request=response.wsgi_request,
                                   kwargs={'pk': other_customer.pk})

        print data['customer']

        response = self.client.put(url, data=data, format='json')
        print(response.data['customer'])
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_put_detail_change_processor(self):
        # TODO
        pass

    def test_put_detail(self):
        method = self.create_payment_method(customer=self.customer)

        url = reverse('payment-method-detail', kwargs={
            'customer_pk': self.customer.pk,
            'payment_method_id': method.pk
        })

        response = self.client.get(url, format='json')
        data = response.data
        data['state'] = PaymentMethod.States.Enabled

        response = self.client.put(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, data)

    def test_get_listing_no_customer(self):
        url = reverse('payment-method-list', kwargs={
            'customer_pk': sys.maxint
        })

        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_detail_no_customer(self):
        url = reverse('payment-method-detail', kwargs={
            'customer_pk': sys.maxint,
            'payment_method_id': 0
        })

        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_detail_no_payment_method(self):
        url = reverse('payment-method-detail', kwargs={
            'customer_pk': self.customer.pk,
            'payment_method_id': sys.maxint
        })

        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_post_listing_no_customer(self):
        processor_url = reverse('payment-processor-detail', kwargs={
            'processor_name': 'manual'
        })

        url = reverse('payment-method-list', kwargs={
            'customer_pk': sys.maxint
        })

        response = self.client.post(url, data={
            'payment_processor': processor_url,
            'state': PaymentMethod.States.Uninitialized
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_post_listing_incomplete_body_1(self):
        url = reverse('payment-method-list', kwargs={
            'customer_pk': 0
        })

        response = self.client.post(url, data={}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_listing_incomplete_body_2(self):
        processor_url = reverse('payment-processor-detail', kwargs={
            'processor_name': 'manual'
        })

        url = reverse('payment-method-list', kwargs={
            'customer_pk': 0
        })

        response = self.client.post(url, data={
            'payment_processor': processor_url
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_put_detail_no_customer(self):
        # TODO
        pass

    def test_put_detail_no_payment_method(self):
        # TODO
        pass

    def test_permissions(self):
        self.assertEqual(PaymentMethodList.permission_classes,
                         (permissions.IsAuthenticated,))
        self.assertEqual(PaymentMethodDetail.permission_classes,
                         (permissions.IsAuthenticated,))

    def test_filter_processor(self):
        method = self.create_payment_method(customer=self.customer)

        url = reverse('payment-method-list', kwargs={
            'customer_pk': self.customer.pk
        })

        url_manual_processor = url + '?processor=manual'
        url_no_output = url + '?processor=random'

        self.assert_get_data(url_manual_processor, [method])
        self.assert_get_data(url_no_output, [])

    def test_filter_state(self):
        method = self.create_payment_method(customer=self.customer,
                                            state=PaymentMethod.States.Enabled)

        url = reverse('payment-method-list', kwargs={
            'customer_pk': self.customer.pk
        })

        url_state_enabled = url + '?state=' + PaymentMethod.States.Enabled
        url_no_output = url + '?state=' + PaymentMethod.States.Disabled

        self.assert_get_data(url_state_enabled, [method])
        self.assert_get_data(url_no_output, [])
