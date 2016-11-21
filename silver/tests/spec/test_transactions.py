from datetime import datetime
from collections import OrderedDict

from rest_framework.reverse import reverse as _reverse
from rest_framework.test import APITestCase

from silver.tests.factories import AdminUserFactory, TransactionFactory, PaymentMethodFactory
from silver.tests.factories import CustomerFactory, PaymentFactory


def reverse(*args, **kwargs):
    return u'http://testserver' + _reverse(*args, **kwargs)

class TestTransactionEndpoint(APITestCase):
    def setUp(self):
        self.user = AdminUserFactory.create()
        self.client.force_authenticate(user=self.user)

    def test_transaction_list(self):
        customer = CustomerFactory.create()
        payment_method = PaymentMethodFactory.create(customer=customer)
        payment = PaymentFactory.create(customer=customer)
        transaction_1 = TransactionFactory.create(payment_method=payment_method, payment=payment)
        expected_t1 = OrderedDict([
            ('url', reverse('transaction-detail',
                            kwargs={'customer_pk': customer.id, 'transaction_uuid': transaction_1.uuid})),
            ('payment_method', reverse('payment-method-detail', kwargs={'customer_pk': customer.id,
                                                                        'payment_method_id': payment_method.id})),
            ('payment', reverse('payment-detail', kwargs={'customer_pk': customer.id,
                                                          'payment_pk': transaction_1.payment.id})),
            ('is_usable', True),
            ('pay_url', reverse('pay-transaction', kwargs={'transaction_uuid': transaction_1.uuid})),
            ('valid_until', None),
        ])
        transaction_2 = TransactionFactory.create(payment_method=payment_method, payment=payment)
        expected_t2 = OrderedDict([
            ('url', reverse('transaction-detail',
                            kwargs={'customer_pk': customer.id, 'transaction_uuid': transaction_2.uuid})),
            ('payment_method', reverse('payment-method-detail', kwargs={'customer_pk': customer.id,
                                                                        'payment_method_id': payment_method.id})),
            ('payment', reverse('payment-detail', kwargs={'customer_pk': customer.id,
                                                          'payment_pk': transaction_2.payment.id})),
            ('is_usable', True),
            ('pay_url', reverse('pay-transaction', kwargs={'transaction_uuid': transaction_2.uuid})),
            ('valid_until', None),
        ])

        url = reverse('transaction-list',
                      kwargs={'customer_pk': customer.id})

        response = self.client.get(url, format='json')
        self.assertEquals(response.data[0], expected_t1)
        self.assertEquals(response.data[1], expected_t2)

    def test_add_transaction(self):
        customer = CustomerFactory.create()
        payment_method = PaymentMethodFactory.create(customer=customer)
        payment = PaymentFactory.create(customer=customer)
        valid_until = datetime.now()
        payment_method_url = reverse('payment-method-detail', kwargs={'customer_pk': customer.pk,
                                                                      'payment_method_id': payment_method.id})
        payment_url = reverse('payment-detail', kwargs={'customer_pk': customer.pk,
                                                        'payment_pk': payment.pk})
        url = reverse('payment-method-transaction-list',
                      kwargs={'customer_pk': customer.pk, 'payment_method_id': payment_method.pk})
        data = {
            'payment_method': reverse('payment-method-detail', kwargs={'customer_pk': customer.pk,
                                                                       'payment_method_id': payment_method.id}),
            'payment': reverse('payment-detail', kwargs={'customer_pk': customer.pk,
                                                         'payment_pk': payment.pk}),
            'valid_until': valid_until
        }

        response = self.client.post(url, format='json', data=data).data

        self.assertEquals(response['payment_method'], payment_method_url)
        self.assertEquals(response['payment'], payment_url)
        self.assertEquals(response['valid_until'][:-1], valid_until.isoformat())
        self.assertEquals(response['is_usable'], False)

    def test_get_transaction_details(self):
        customer = CustomerFactory.create()
        payment_method = PaymentMethodFactory.create(customer=customer)
        payment = PaymentFactory.create(customer=customer)
        transaction_1 = TransactionFactory.create(payment_method=payment_method, payment=payment)
        expected_t1 = OrderedDict([
            ('url', reverse('transaction-detail',
                            kwargs={'customer_pk': customer.pk, 'transaction_uuid': transaction_1.uuid})),
            ('payment_method', reverse('payment-method-detail', kwargs={'customer_pk': customer.pk,
                                                                        'payment_method_id': payment_method.id})),
            ('payment', reverse('payment-detail', kwargs={'customer_pk': customer.pk,
                                                          'payment_pk': transaction_1.payment.pk})),
            ('is_usable', True),
            ('pay_url', reverse('pay-transaction', kwargs={'transaction_uuid': transaction_1.uuid})),
            ('valid_until', None),
        ])

        url = reverse('transaction-detail',
                      kwargs={'customer_pk': customer.pk,
                              'transaction_uuid': transaction_1.uuid})
        response = self.client.get(url, format='json')
        self.assertEquals(response.data, dict(expected_t1))

    def test_modify_one(self):
        customer = CustomerFactory.create()
        payment_method = PaymentMethodFactory.create(customer=customer)
        payment = PaymentFactory.create(customer=customer)
        transaction_1 = TransactionFactory.create(payment_method=payment_method, payment=payment)
        valid_until = datetime.now()
        url = reverse('transaction-detail',
                      kwargs={'customer_pk': customer.id,
                              'transaction_uuid': transaction_1.uuid})
        data = {
            'payment': reverse('payment-detail', kwargs={'customer_pk': customer.id,
                                                         'payment_pk': payment_method.id}),
            'valid_until': valid_until
        }

        response = self.client.put(url, format='json', data=data)
        self.assertEquals(response.data['detail'], 'Method "PUT" not allowed.')

        response = self.client.post(url, format='json', data=data)
        self.assertEquals(response.data['detail'], 'Method "POST" not allowed.')

        response = self.client.patch(url, format='json', data=data)
        self.assertEquals(response.data['detail'], 'Method "PATCH" not allowed.')

    def test_create_one_without_required_fields(self):
        customer = CustomerFactory.create()
        payment_method = PaymentMethodFactory.create(customer=customer)
        payment = PaymentFactory.create(customer=customer)
        transaction = TransactionFactory.create(payment_method=payment_method, payment=payment)
        valid_until = datetime.now()
        url = reverse('transaction-detail',
                      kwargs={'customer_pk': customer.id,
                              'transaction_uuid': transaction.uuid})
        data = {
            'payment': reverse('payment-detail', kwargs={'customer_pk': customer.id,
                                                         'payment_pk': payment.id}),
            'valid_until': valid_until
        }

        url = reverse('payment-method-transaction-list',
                      kwargs={'customer_pk': customer.id, 'payment_method_id': payment_method.id})

        response = self.client.post(url, format='json', data=data)
        self.assertEquals(response.data['payment_method'], ['This field is required.'])
