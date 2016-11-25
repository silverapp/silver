from datetime import datetime
from collections import OrderedDict
from functools import wraps

from rest_framework import status
from rest_framework.reverse import reverse as _reverse
from rest_framework.test import APITestCase

from silver.models import Transaction, PaymentProcessorManager
from silver.models.payment_processors.generics import GenericPaymentProcessor
from silver.models.payment_processors.generics import TriggeredProcessorMixin
from silver.tests.factories import (AdminUserFactory, TransactionFactory,
                                    PaymentMethodFactory)
from silver.tests.factories import CustomerFactory, PaymentFactory


def reverse(*args, **kwargs):
    return u'http://testserver' + _reverse(*args, **kwargs)


def register(func):
    class SomeProcessor(GenericPaymentProcessor, TriggeredProcessorMixin):
        name = 'SomeProcessor'
        transaction_class = Transaction

        @staticmethod
        def setup(data=None):
            pass

    @wraps(func)
    def func_wrapper(cls, *args, **kwargs):
        PaymentProcessorManager.register(SomeProcessor)
        result = func(cls, *args, **kwargs)
        PaymentProcessorManager.unregister(SomeProcessor)
        return result

    return func_wrapper


class TestTransactionEndpoint(APITestCase):
    def setUp(self):
        self.user = AdminUserFactory.create()
        self.client.force_authenticate(user=self.user)

    def test_transaction_list(self):
        customer = CustomerFactory.create()
        payment_method = PaymentMethodFactory.create(customer=customer)
        payment = PaymentFactory.create(customer=customer)

        transaction_1 = TransactionFactory.create(
            payment_method=payment_method, payment=payment)
        expected_t1 = self._transaction_data(customer, payment,
                                             payment_method, transaction_1)

        transaction_2 = TransactionFactory.create(
            payment_method=payment_method, payment=payment)
        expected_t2 = self._transaction_data(customer, payment,
                                             payment_method, transaction_2)

        url = reverse('transaction-list',
                      kwargs={'customer_pk': customer.pk})

        response = self.client.get(url, format='json')
        self.assertEqual(response.data[0], expected_t1)
        self.assertEqual(response.data[1], expected_t2)

    def test_add_transaction(self):
        customer = CustomerFactory.create()
        payment_method = PaymentMethodFactory.create(customer=customer)
        payment = PaymentFactory.create(customer=customer)
        valid_until = datetime.now()
        payment_method_url = reverse('payment-method-detail',
                                     kwargs={'customer_pk': customer.pk,
                                             'payment_method_id': payment_method.id})
        payment_url = reverse('payment-detail',
                              kwargs={'customer_pk': customer.pk,
                                      'payment_pk': payment.pk})
        url = reverse('payment-method-transaction-list',
                      kwargs={'customer_pk': customer.pk,
                              'payment_method_id': payment_method.pk})
        data = {
            'payment_method': reverse('payment-method-detail',
                                      kwargs={'customer_pk': customer.pk,
                                              'payment_method_id': payment_method.id}),
            'payment': reverse('payment-detail',
                               kwargs={'customer_pk': customer.pk,
                                       'payment_pk': payment.pk}),
            'valid_until': valid_until
        }

        response = self.client.post(url, format='json', data=data).data

        self.assertEqual(response['payment_method'], payment_method_url)
        self.assertEqual(response['payment'], payment_url)
        self.assertEqual(response['valid_until'][:-1], valid_until.isoformat())
        self.assertEqual(response['is_usable'], False)

    def test_get_transaction_details(self):
        customer = CustomerFactory.create()
        payment_method = PaymentMethodFactory.create(customer=customer)
        payment = PaymentFactory.create(customer=customer)
        transaction_1 = TransactionFactory.create(
            payment_method=payment_method, payment=payment)
        expected_t1 = OrderedDict([
            ('url', reverse('transaction-detail',
                            kwargs={'customer_pk': customer.pk,
                                    'transaction_uuid': transaction_1.uuid})),
            ('payment_method', reverse('payment-method-detail',
                                       kwargs={'customer_pk': customer.pk,
                                               'payment_method_id': payment_method.id})),
            ('payment',
             reverse('payment-detail', kwargs={'customer_pk': customer.pk,
                                               'payment_pk': transaction_1.payment.pk})),
            ('is_usable', True),
            ('pay_url', reverse('pay-transaction', kwargs={
                'transaction_uuid': transaction_1.uuid})),
            ('valid_until', None),
        ])

        url = reverse('transaction-detail',
                      kwargs={'customer_pk': customer.pk,
                              'transaction_uuid': transaction_1.uuid})
        response = self.client.get(url, format='json')
        self.assertEqual(response.data, dict(expected_t1))

    def test_modify_one(self):
        customer = CustomerFactory.create()
        payment_method = PaymentMethodFactory.create(customer=customer)
        payment = PaymentFactory.create(customer=customer)
        transaction_1 = TransactionFactory.create(
            payment_method=payment_method, payment=payment)
        valid_until = datetime.now()
        url = reverse('transaction-detail',
                      kwargs={'customer_pk': customer.id,
                              'transaction_uuid': transaction_1.uuid})
        data = {
            'payment': reverse('payment-detail',
                               kwargs={'customer_pk': customer.id,
                                       'payment_pk': payment_method.id}),
            'valid_until': valid_until
        }

        response = self.client.put(url, format='json', data=data)
        self.assertEqual(response.data['detail'], 'Method "PUT" not allowed.')

        response = self.client.post(url, format='json', data=data)
        self.assertEqual(response.data['detail'], 'Method "POST" not allowed.')

        response = self.client.patch(url, format='json', data=data)
        self.assertEqual(response.data['detail'],
                         'Method "PATCH" not allowed.')

    def test_create_one_without_required_fields(self):
        customer = CustomerFactory.create()
        payment_method = PaymentMethodFactory.create(customer=customer)
        payment = PaymentFactory.create(customer=customer)
        transaction = TransactionFactory.create(payment_method=payment_method,
                                                payment=payment)
        valid_until = datetime.now()
        url = reverse('transaction-detail',
                      kwargs={'customer_pk': customer.id,
                              'transaction_uuid': transaction.uuid})
        data = {
            'payment': reverse('payment-detail',
                               kwargs={'customer_pk': customer.id,
                                       'payment_pk': payment.id}),
            'valid_until': valid_until
        }

        url = reverse('payment-method-transaction-list',
                      kwargs={'customer_pk': customer.id,
                              'payment_method_id': payment_method.id})

        response = self.client.post(url, format='json', data=data)
        self.assertEqual(response.data['payment_method'],
                         ['This field is required.'])

    @register
    def test_filter_payment_method(self):
        customer = CustomerFactory.create()
        payment = PaymentFactory.create(customer=customer)
        payment_method = PaymentMethodFactory.create(
            payment_processor='someprocessor',
            customer=customer)

        transaction1 = TransactionFactory.create(
            payment_method=payment_method,
            payment=payment
        )
        transaction_data_1 = self._transaction_data(customer, payment,
                                                    payment_method,
                                                    transaction1)

        transaction2 = TransactionFactory.create(
            payment_method=payment_method,
            payment=payment
        )
        transaction_data_2 = self._transaction_data(customer, payment,
                                                    payment_method,
                                                    transaction2)

        urls = [
            reverse(
                'payment-method-transaction-list', kwargs={
                    'customer_pk': customer.pk,
                    'payment_method_id': payment_method.pk}),
            reverse(
                'transaction-list', kwargs={'customer_pk': customer.pk})]

        for url in urls:
            url_method_someprocessor = url + '?payment_method=someprocessor'
            url_no_output = url + '?payment_method=Random'

            response = self.client.get(url_method_someprocessor, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data[0], transaction_data_1)
            self.assertEqual(response.data[1], transaction_data_2)

            response = self.client.get(url_no_output, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data, [])

    @register
    def test_filter_min_max_amount(self):
        customer = CustomerFactory.create()
        payment = PaymentFactory.create(customer=customer, amount=100)
        payment_method_ok = PaymentMethodFactory.create(
            payment_processor='someprocessor',
            customer=customer)

        transaction = TransactionFactory.create(
            payment_method=payment_method_ok,
            payment=payment
        )
        transaction_data = self._transaction_data(customer, payment,
                                                  payment_method_ok,
                                                  transaction)

        urls = [
            reverse(
                'payment-method-transaction-list', kwargs={
                    'customer_pk': customer.pk,
                    'payment_method_id': payment_method_ok.pk}),
            reverse(
                'transaction-list', kwargs={'customer_pk': customer.pk})]

        for url in urls:
            url_with_filterable_data = url + '?min_amount=10'
            url_no_output = url + '?min_amount=150'

            response = self.client.get(url_with_filterable_data, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data[0], transaction_data)

            response = self.client.get(url_no_output, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data, [])

            url_with_filterable_data = url + '?max_amount=1050'
            url_no_output = url + '?max_amount=10'

            response = self.client.get(url_with_filterable_data, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data[0], transaction_data)

            response = self.client.get(url_no_output, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data, [])

    @register
    def test_filter_disabled(self):
        customer = CustomerFactory.create()
        payment = PaymentFactory.create(customer=customer, amount=100)
        payment_method = PaymentMethodFactory.create(
            payment_processor='someprocessor',
            customer=customer)

        transaction = TransactionFactory.create(
            payment_method=payment_method,
            payment=payment,
            disabled=False
        )
        transaction_data = self._transaction_data(customer, payment,
                                                      payment_method,
                                                      transaction)

        urls = [
            reverse(
                'payment-method-transaction-list', kwargs={
                    'customer_pk': customer.pk,
                    'payment_method_id': payment_method.pk}),
            reverse(
                'transaction-list', kwargs={'customer_pk': customer.pk})]

        for url in urls:
            url_not_disabled = url + '?disabled=False'
            url_no_output = url + '?disabled=True'

            response = self.client.get(url_not_disabled, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data[0], transaction_data)

            response = self.client.get(url_no_output, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data, [])

    def _transaction_data(self, customer, payment, payment_method,
                          transaction):
        return OrderedDict([
            ('url', reverse('transaction-detail',
                            kwargs={'customer_pk': customer.pk,
                                    'transaction_uuid': transaction.uuid})),
            ('payment_method', reverse('payment-method-detail',
                                       kwargs={'customer_pk': customer.pk,
                                               'payment_method_id': payment_method.pk})),
            ('payment', reverse('payment-detail',
                                kwargs={'customer_pk': customer.pk,
                                        'payment_pk': payment.pk})),
            ('is_usable', True),
            ('pay_url', reverse('pay-transaction',
                                kwargs={'transaction_uuid': transaction.uuid})),
            ('valid_until', None),
        ])
