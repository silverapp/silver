import json
from collections import OrderedDict
from decimal import Decimal
from mock import patch, MagicMock

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from silver.models import Payment
from silver.tests.factories import InvoiceFactory, AdminUserFactory, PaymentFactory


class TestPaymentEndpoints(APITestCase):
    def setUp(self):
        admin_user = AdminUserFactory.create()
        self.client.force_authenticate(user=admin_user)

    def test_get_payment_list(self):
        initial_payment = PaymentFactory.create()
        initial_payment.amount = Decimal('10.00')
        initial_payment.save()

        customer = initial_payment.customer
        proforma = initial_payment.proforma
        invoice = initial_payment.invoice
        provider = initial_payment.provider

        url = reverse(
            'payment-list', kwargs={'customer_pk': initial_payment.customer.pk}
        )

        response = self.client.get(url, format='json')

        assert response.status_code == status.HTTP_200_OK

        assert response.data == [OrderedDict([
            ('id', initial_payment.pk),
            ('url', 'http://testserver/customers/%d/payments/%d/' % (
                customer.pk, initial_payment.pk
            )),
            ('customer', 'http://testserver/customers/%d/' % customer.pk),
            ('provider', 'http://testserver/providers/%d/' % provider.pk),
            ('amount', u'10.00'),
            ('currency', 'USD'),
            ('due_date', None),
            ('status', 'unpaid'),
            ('visible', True),
            ('proforma', 'http://testserver/proformas/%d/' % proforma.pk),
            ('invoice', 'http://testserver/invoices/%d/' % invoice.pk)
        ])]

        payments = PaymentFactory.create_batch(2)

        for payment in payments:
            payment.customer = initial_payment.customer
            payment.save()

        response = self.client.get(url, format='json')

        assert response.status_code == status.HTTP_200_OK

        assert len(response.data) == 3

    def test_get_payment_detail(self):
        payment = PaymentFactory.create()
        payment.amount = Decimal('10.00')
        payment.save()

        customer = payment.customer
        proforma = payment.proforma
        invoice = payment.invoice
        provider = payment.provider

        url = reverse(
            'payment-detail', kwargs={'customer_pk': payment.customer.pk,
                                      'payment_pk': payment.pk}
        )

        response = self.client.get(url, format='json')

        assert response.status_code == status.HTTP_200_OK

        assert response.data == {
            'customer': 'http://testserver/customers/%d/' % customer.pk,
            'provider': 'http://testserver/providers/%d/' % provider.pk,
            'due_date': None,
            'url': 'http://testserver/customers/%d/payments/%d/' % (
                customer.pk, payment.pk
            ),
            'proforma': 'http://testserver/proformas/%d/' % proforma.pk,
            'visible': True,
            'amount': u'10.00',
            'currency': 'USD',
            'status': 'unpaid',
            'invoice': 'http://testserver/invoices/%d/' % invoice.pk,
            'id': payment.pk,
        }

    def test_post_payment(self):
        invoice = InvoiceFactory.create()
        customer = invoice.customer

        url = reverse(
            'payment-list', kwargs={'customer_pk': invoice.customer.pk}
        )

        data = {
            'due_date': None,
            'visible': True,
            'amount': 10.00,
            'currency': 'USD',
            'status': 'unpaid',
            'provider': 'http://testserver/providers/%d/' % invoice.provider.pk,
            'invoice': 'http://testserver/invoices/%d/' % invoice.pk
        }

        response = self.client.post(
            url, json.dumps(data), content_type='application/json'
        )

        assert response.status_code == status.HTTP_201_CREATED

        expected_data = {
            'customer': 'http://testserver/customers/%d/' % customer.pk,
            'due_date': None,
            'proforma': None,
            'visible': True,
            'amount': u'10.00',
            'currency': u'USD',
            'status': 'unpaid',
            'invoice': 'http://testserver/invoices/%d/' % invoice.pk,
        }

        for key in expected_data:
            assert expected_data[key] == response.data[key]

        payment_id = response.data['id']

        assert Payment.objects.filter(id=payment_id)

    def test_post_payment_with_invalid_fields(self):
        invoice = InvoiceFactory.create()
        customer = invoice.customer

        url = reverse(
            'payment-list', kwargs={'customer_pk': invoice.customer.pk}
        )

        data = {
            'due_date': "yesterday",
            'visible': "maybe",
            'amount': -10.00,
            'currency': 'USD',
            'status': 'prepaid',
            'provider': 'http://testserver/providers/1234/',
            'invoice': 'http://testserver/invoices/4321/'
        }

        response = self.client.post(
            url, json.dumps(data), content_type='application/json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

        self.assertEquals(
            response.data,
            {
                'status': [u'"prepaid" is not a valid choice.'],
                'due_date': [
                    u'Date has wrong format. '
                    u'Use one of these formats instead: YYYY[-MM[-DD]].'
                ],
                'visible': [u'"maybe" is not a valid boolean.'],
                'amount': [u'Ensure this value is greater than or equal to 0.00.'],
                'invoice': [u'Invalid hyperlink - Object does not exist.'],
                'provider': [u'Invalid hyperlink - Object does not exist.']
            }
        )

    def test_patch_payment(self):
        payment = PaymentFactory.create()
        invoice = payment.invoice
        proforma = payment.proforma
        invoice.proforma = proforma
        invoice.save()
        payment.provider = invoice.provider
        payment.customer = invoice.customer
        payment.save()

        url = reverse(
            'payment-detail', kwargs={'customer_pk': payment.customer.pk,
                                      'payment_pk': payment.pk}
        )

        data = {
            'due_date': '2016-10-20',
            'visible': False,
            'amount': 330.00,
            'currency': 'RON',
        }

        response = self.client.patch(
            url, json.dumps(data), content_type='application/json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data == {
            'customer': u'http://testserver/customers/%d/' % payment.customer.pk,
            'due_date': '2016-10-20',
            'visible': False,
            'url': u'http://testserver/customers/%d/payments/%d/' % (payment.customer.pk,
                                                                     payment.pk),
            'currency': u'RON',
            'amount': u'330.00',
            'status': 'unpaid',
            'proforma': u'http://testserver/proformas/%d/' % proforma.pk,
            'invoice': u'http://testserver/invoices/%d/' % invoice.pk,
            'provider': u'http://testserver/providers/%d/' % payment.provider.pk,
            'id': payment.pk
        }

    def test_paid_status_payment_no_updates(self):
        payment = PaymentFactory.create()

        url = reverse(
            'payment-detail', kwargs={'customer_pk': payment.customer.pk,
                                      'payment_pk': payment.pk}
        )

        payment.status = payment.Status.Paid
        payment.save()

        data = {
            'due_date': '2016-10-20',
            'visible': False,
        }

        response = self.client.patch(
            url, json.dumps(data), content_type='application/json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == {
            u'non_field_errors': [u"Cannot update a payment with 'paid' status."]
        }

    def test_canceled_status_payment_no_updates(self):
        payment = PaymentFactory.create()

        url = reverse(
            'payment-detail', kwargs={'customer_pk': payment.customer.pk,
                                      'payment_pk': payment.pk}
        )

        payment.status = payment.Status.Canceled
        payment.save()

        data = {
            'due_date': '2016-10-20',
            'visible': False,
        }

        response = self.client.patch(
            url, json.dumps(data), content_type='application/json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == {
            u'non_field_errors': [u"Cannot update a payment with 'canceled' status."]
        }

    def test_valid_status_transition_from_unpaid_to_pending(self):
        process_mock = MagicMock()
        fail_mock = MagicMock()
        succeed_mock = MagicMock()
        cancel_mock = MagicMock()

        with patch.multiple('silver.models.payments.Payment',
                            process=process_mock,
                            fail=fail_mock,
                            succeed=succeed_mock,
                            cancel=cancel_mock):

            payment = PaymentFactory.create()
            invoice = payment.invoice
            proforma = payment.proforma
            invoice.proforma = proforma
            invoice.save()
            payment.provider = invoice.provider
            payment.customer = invoice.customer
            payment.save()

            url = reverse(
                'payment-detail', kwargs={'customer_pk': payment.customer.pk,
                                          'payment_pk': payment.pk}
            )

            data = {
                'status': payment.Status.Pending
            }

            response = self.client.patch(
                url, json.dumps(data), content_type='application/json'
            )

            print response.status_code, response.data
            assert response.status_code == status.HTTP_200_OK
            assert process_mock.call_count == 1

    def test_valid_status_transitions_from_pending_to_unpaid(self):
        process_mock = MagicMock()
        fail_mock = MagicMock()
        succeed_mock = MagicMock()
        cancel_mock = MagicMock()

        with patch.multiple('silver.models.payments.Payment',
                            process=process_mock,
                            fail=fail_mock,
                            succeed=succeed_mock,
                            cancel=cancel_mock):
            payment = PaymentFactory.create()
            invoice = payment.invoice
            proforma = payment.proforma
            invoice.proforma = proforma
            invoice.save()
            payment.provider = invoice.provider
            payment.customer = invoice.customer
            payment.save()

            url = reverse(
                'payment-detail',
                kwargs={'customer_pk': payment.customer.pk,
                        'payment_pk': payment.pk}
            )

            payment.status = payment.Status.Pending
            payment.save()
            data = {
                'status': payment.Status.Unpaid
            }

            response = self.client.patch(
                url, json.dumps(data), content_type='application/json'
            )

            assert response.status_code == status.HTTP_200_OK
            assert fail_mock.call_count == 1

    def test_valid_status_transitions_from_unpaid_to_cancel(self):
        process_mock = MagicMock()
        fail_mock = MagicMock()
        succeed_mock = MagicMock()
        cancel_mock = MagicMock()

        with patch.multiple('silver.models.payments.Payment',
                            process=process_mock,
                            fail=fail_mock,
                            succeed=succeed_mock,
                            cancel=cancel_mock):
            payment = PaymentFactory.create()
            invoice = payment.invoice
            proforma = payment.proforma
            invoice.proforma = proforma
            invoice.save()
            payment.provider = invoice.provider
            payment.customer = invoice.customer
            payment.save()

            url = reverse(
                'payment-detail',
                kwargs={'customer_pk': payment.customer.pk,
                        'payment_pk': payment.pk}
            )

            data = {
                'status': payment.Status.Canceled
            }

            response = self.client.patch(
                url, json.dumps(data), content_type='application/json'
            )

            assert response.status_code == status.HTTP_200_OK
            assert cancel_mock.call_count == 1

    def test_valid_status_transition_from_unpaid_to_paid(self):
        process_mock = MagicMock()
        fail_mock = MagicMock()
        succeed_mock = MagicMock()
        cancel_mock = MagicMock()

        with patch.multiple('silver.models.payments.Payment',
                            process=process_mock,
                            fail=fail_mock,
                            succeed=succeed_mock,
                            cancel=cancel_mock):
            payment = PaymentFactory.create()
            invoice = payment.invoice
            proforma = payment.proforma
            invoice.proforma = proforma
            invoice.save()
            payment.provider = invoice.provider
            payment.customer = invoice.customer
            payment.save()

            url = reverse(
                'payment-detail',
                kwargs={'customer_pk': payment.customer.pk,
                        'payment_pk': payment.pk}
            )

            data = {
                'status': payment.Status.Paid
            }

            response = self.client.patch(
                url, json.dumps(data), content_type='application/json'
            )

            assert response.status_code == status.HTTP_200_OK
            assert succeed_mock.call_count == 1
