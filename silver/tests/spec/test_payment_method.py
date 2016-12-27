import sys

from copy import deepcopy

from django.test import override_settings
from six import iteritems

from rest_framework import permissions, status
from rest_framework.reverse import reverse

from silver.api.serializers import PaymentMethodSerializer
from silver.models import PaymentMethod
from silver.models.payment_processors.base import PaymentProcessorBase
from silver.models.payment_processors.mixins import TriggeredProcessorMixin
from silver.api.views import PaymentMethodList, PaymentMethodDetail
from silver.tests.spec.util.api_get_assert import APIGetAssert
from silver.tests.factories import CustomerFactory, PaymentMethodFactory


class SomeProcessor(PaymentProcessorBase, TriggeredProcessorMixin):
    @staticmethod
    def setup(data=None):
        pass


PAYMENT_PROCESSORS = {
    'manual': {
        'path': 'silver.models.payment_processors.manual.ManualProcessor',
        'display_name': 'Manual'
    },
    'someprocessor': {
        'path': 'silver.tests.spec.test_payment_processors.SomeProcessor',
        'display_name': 'SomeProcessor'
    }
}


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
            'state': PaymentMethod.States.Uninitialized
        }, format='json')

        payment_method = PaymentMethod.objects.get(customer=self.customer)
        self.assert_get_data(response.data['url'], payment_method)

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
        self.assertEqual(response.data, {
            'non_field_errors':
                ["If 'additional_data' is specified,"
                 " then 'state' must be one of (unverified, enabled)."]})

    def test_post_listing_invalid_initial_state(self):
        invalid_initial_states = PaymentMethod.States.invalid_initial_states()
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
            self.assertEqual(response.data, {
                'state': [u'Must initially be one of (uninitialized, '
                          u'unverified, enabled).']
            })

    def test_put_detail_state_transitions(self):
        states = PaymentMethod.States.as_list()
        permutations = [(old, new) for old in states for new in states]

        valid_transitions = set()
        for _, transition in iteritems(PaymentMethod.state_transitions):
            if isinstance(transition['source'], (tuple, list)):
                unmerged_transitions = set([(old, transition['target']) for
                                            old in transition['source']])
            else:
                unmerged_transitions = {(transition['source'],
                                         transition['target'])}

            valid_transitions = valid_transitions.union(unmerged_transitions)

        # add x -> x transitions as they are allowed
        valid_transitions = valid_transitions.union(
            set([(x, x) for x in states]))

        valid_transition_list = list(valid_transitions)

        for old, new in permutations:
            payment_method = self.create_payment_method(customer=self.customer,
                                                        state=old)

            url = reverse('payment-method-detail', kwargs={
                'customer_pk': self.customer.pk,
                'payment_method_id': payment_method.pk
            })
            response = self.client.get(url, format='json')

            data = response.data
            data['state'] = new

            response = self.client.put(url, data=data, format='json')

            message = '{} -> {}: code got {{}} expected {{}}'.format(old, new)
            if (old, new) in valid_transition_list:
                self.assertEqual(response.status_code,
                                 status.HTTP_200_OK,
                                 message.format(response.status_code,
                                                status.HTTP_200_OK))
                self.assertEqual(data, response.data,
                                 message.format(response.status_code,
                                                status.HTTP_200_OK))
            else:
                self.assertEqual(response.status_code,
                                 status.HTTP_409_CONFLICT,
                                 message.format(response.status_code,
                                                status.HTTP_409_CONFLICT))

    def test_put_detail_additional_data_disabled_state(self):
        payment_method = self.create_payment_method(customer=self.customer,
                                                    state=PaymentMethod.States.Disabled)

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

    @override_settings(PAYMENT_PROCESSORS=PAYMENT_PROCESSORS)
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
                                                    state=PaymentMethod.States.Unverified)

        url = reverse('payment-method-detail', kwargs={
            'customer_pk': self.customer.pk,
            'payment_method_id': payment_method.pk
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
            'state': PaymentMethod.States.Uninitialized
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

    def test_post_listing_missing_initial_state(self):
        processor_url = reverse('payment-processor-detail', kwargs={
            'processor_name': 'manual'
        })

        url = reverse('payment-method-list', kwargs={
            'customer_pk': self.customer.pk
        })

        response = self.client.post(url, data={
            'payment_processor': processor_url
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['state'],
                         PaymentMethod.States.Uninitialized)

        payment_method = PaymentMethod.objects.get(customer=self.customer)
        self.assert_get_data(response.data['url'], payment_method)

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

    def test_filter_state(self):
        payment_method = self.create_payment_method(customer=self.customer,
                                                    state=PaymentMethod.States.Enabled)

        url = reverse('payment-method-list', kwargs={
            'customer_pk': self.customer.pk
        })

        url_state_enabled = url + '?state=' + PaymentMethod.States.Enabled
        url_no_output = url + '?state=' + PaymentMethod.States.Disabled

        self.assert_get_data(url_state_enabled, [payment_method])
        self.assert_get_data(url_no_output, [])
