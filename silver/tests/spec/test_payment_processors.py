from collections import OrderedDict

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from silver.models.payment_processors.managers import PaymentProcessorManager
from silver.models.payment_processors.generics import (GenericPaymentProcessor,
                                                       TriggeredProcessorMixin)
from silver.tests.factories import AdminUserFactory


class TestPaymentProcessorsEndpoints(APITestCase):
    def setUp(self):
        admin_user = AdminUserFactory.create()
        self.client.force_authenticate(user=admin_user)

    def test_payment_processors_list(self):
        url = reverse('payment-processor-list')
        response = self.client.get(url, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data == [OrderedDict([
            ('name', u'Manual'),
            ('type', u'manual'),
            ('url', 'http://testserver/payment_processors/Manual/')
        ])]

        class SomeProcessor(GenericPaymentProcessor, TriggeredProcessorMixin):
            name = "SomeProcessor"
            @staticmethod
            def setup(data=None):
                pass

        PaymentProcessorManager.register(SomeProcessor)

        assert response.status_code == status.HTTP_200_OK
        assert response.data == [OrderedDict([
            ('name', u'Manual'),
            ('type', u'manual'),
            ('url', 'http://testserver/payment_processors/Manual/')
        ])]

    def test_payment_processors_detail(self):
        url = reverse('payment-processor-detail', kwargs={
            'processor_name': 'Manual'
        })
        response = self.client.get(url, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data == {
            'url': 'http://testserver/payment_processors/Manual/',
            'type': u'manual',
            'name': u'Manual'
        }