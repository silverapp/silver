import json
from collections import OrderedDict
from datetime import timedelta, datetime
from decimal import Decimal

import pytz
from mock import patch, MagicMock
from rest_framework import status
from rest_framework.reverse import reverse

from silver.api.serializers import PaymentSerializer
from silver.models import Payment, Provider
from silver.tests.factories import (InvoiceFactory, PaymentFactory,
                                    CustomerFactory)
from silver.tests.spec.util.api_get_assert import APIGetAssert


class TestPaymentEndpoints(APIGetAssert):
    serializer_class = PaymentSerializer

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

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data, {
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
        })

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

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

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
            self.assertEqual(expected_data[key], response.data[key])

        payment_id = response.data['id']

        assert Payment.objects.filter(id=payment_id)

    def test_post_get_payments(self):
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

        payment = self.client.post(
            url, json.dumps(data), content_type='application/json'
        ).data
        payment_url = 'http://testserver/customers/%d/payments/%d/' % (
            customer.pk, payment['id'])

        expected_data = [{
            'customer': 'http://testserver/customers/%d/' % customer.pk,
            'due_date': None,
            'proforma': None,
            'visible': True,
            'url': payment_url,
            'amount': u'10.00',
            'currency': u'USD',
            'status': 'unpaid',
            'invoice': 'http://testserver/invoices/%d/' % invoice.pk,
            'provider': 'http://testserver/providers/%d/' % invoice.provider.pk,
            'id': payment['id']
        }]

        response = self.client.get(url, content_type='application/json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data == expected_data

    def test_post_payment_with_invalid_fields(self):
        invoice = InvoiceFactory.create()
        customer = invoice.customer

        url = reverse(
            'payment-list', kwargs={'customer_pk': customer.pk}
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
                'amount': [
                    u'Ensure this value is greater than or equal to 0.00.'],
                'invoice': [u'Invalid hyperlink - Object does not exist.'],
                'provider': [u'Invalid hyperlink - Object does not exist.']
            }
        )

    def test_post_payment_with_invalid_fields_get(self):
        invoice = InvoiceFactory.create()
        customer = invoice.customer

        url = reverse(
            'payment-list', kwargs={'customer_pk': customer.pk}
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

        self.client.post(
            url, json.dumps(data), content_type='application/json'
        )

        response = self.client.get(url, content_type='application/json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data == []

    def test_put_payment_not_allowed(self):
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
            'customer': 'http://testserver/customers/%d/' % payment.customer.pk,
            'amount': 0.10,
            'currency': 'RON',
            'provider': 'http://testserver/providers/%d/' % payment.provider.pk
        }

        response = self.client.put(
            url, json.dumps(data), content_type='application/json'
        )

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert response.data == {u'detail': u'Method "PUT" not allowed.'}

    def test_put_payment_not_allowed_get(self):
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

        initial_payment = self.client.get(
            url, content_type='application/json'
        ).data

        data = {
            'customer': 'http://testserver/customers/%d/' % payment.customer.pk,
            'amount': 0.10,
            'currency': 'RON',
            'provider': 'http://testserver/providers/%d/' % payment.provider.pk
        }

        self.client.put(
            url, json.dumps(data), content_type='application/json'
        )

        response = self.client.get(url, content_type='application/json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data == initial_payment

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

        final_payment = self.client.get(
            url, content_type='application/json'
        ).data

        final_payment['status'] = 'paid'

        data = {'status': payment.Status.Paid}

        response = self.client.patch(
            url, json.dumps(data), content_type='application/json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data == final_payment

    def test_patch_other_than_status_fail(self):
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
            'amount': 100.00,
            'currency': u'RON'
        }

        response = self.client.patch(
            url, json.dumps(data), content_type='application/json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == {
            u'non_field_errors': [
                u"Existing payments only accept updating their status. [u'amount', u'currency'] given."]
        }

    def test_patch_other_than_status_fail_and_get(self):
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

        initial_payment = self.client.get(
            url, content_type='application/json'
        ).data

        data = {
            'amount': 100.00,
            'currency': u'RON'
        }

        self.client.patch(
            url, json.dumps(data), content_type='application/json'
        )

        response = self.client.get(
            url, content_type='application/json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data == initial_payment

    def test_paid_status_payment_failed_status_update(self):
        payment = PaymentFactory.create()

        url = reverse(
            'payment-detail', kwargs={'customer_pk': payment.customer.pk,
                                      'payment_pk': payment.pk}
        )

        payment.status = payment.Status.Paid
        payment.save()

        data = {'status': payment.Status.Pending}

        response = self.client.patch(
            url, json.dumps(data), content_type='application/json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == {
            u'non_field_errors': [
                u"Cannot update a payment with 'paid' status."]
        }

    def test_paid_status_payment_no_updates_on_get(self):
        payment = PaymentFactory.create()

        url = reverse(
            'payment-detail', kwargs={'customer_pk': payment.customer.pk,
                                      'payment_pk': payment.pk}
        )

        payment.status = payment.Status.Paid
        payment.save()

        initial_payment = self.client.get(
            url, content_type='application/json'
        ).data

        data = {
            'due_date': '2016-10-20',
            'visible': False,
        }

        self.client.patch(
            url, json.dumps(data), content_type='application/json'
        )

        response = self.client.get(
            url, content_type='application/json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data == initial_payment

    def test_canceled_status_payment_failed_status_update(self):
        payment = PaymentFactory.create()

        url = reverse(
            'payment-detail', kwargs={'customer_pk': payment.customer.pk,
                                      'payment_pk': payment.pk}
        )

        payment.status = payment.Status.Canceled
        payment.save()

        data = {'status': payment.Status.Unpaid}

        response = self.client.patch(
            url, json.dumps(data), content_type='application/json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == {
            u'non_field_errors': [
                u"Cannot update a payment with 'canceled' status."]
        }

    def test_canceled_status_payment_no_updates_on_get(self):
        payment = PaymentFactory.create()

        url = reverse(
            'payment-detail', kwargs={'customer_pk': payment.customer.pk,
                                      'payment_pk': payment.pk}
        )

        payment.status = payment.Status.Canceled
        payment.save()

        initial_payment = self.client.get(
            url, content_type='application/json'
        ).data

        data = {
            'due_date': '2016-10-20',
            'visible': False,
        }

        self.client.patch(
            url, json.dumps(data), content_type='application/json'
        )

        response = self.client.get(
            url, content_type='application/json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data == initial_payment

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

            assert response.status_code == status.HTTP_200_OK
            assert process_mock.call_count == 1

    def test_get_after_valid_status_transition_from_unpaid_to_pending(self):
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

        self.client.patch(
            url, json.dumps(data), content_type='application/json'
        )

        response = self.client.get(
            url, content_type='application/json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data.get('status') == 'pending'

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

    def test_get_after_valid_status_transitions_from_pending_to_unpaid(self):
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

        self.client.patch(
            url, json.dumps(data), content_type='application/json'
        )

        response = self.client.get(
            url, content_type='application/json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data.get('status') == 'unpaid'

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

    def test_get_after_valid_status_transitions_from_unpaid_to_cancel(self):
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

        self.client.patch(
            url, json.dumps(data), content_type='application/json'
        )

        response = self.client.get(
            url, content_type='application/json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data.get('status') == 'canceled'

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

    def test_get_after_valid_status_transition_from_unpaid_to_paid(self):
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

        self.client.patch(
            url, json.dumps(data), content_type='application/json'
        )

        response = self.client.get(
            url, content_type='application/json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data.get('status') == 'paid'

    def test_final_status_failed_update(self):
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

        initial_payment = self.client.get(
            url, content_type='application/json'
        ).data

        initial_currency = initial_payment['currency']

        for final_status in Payment.Status.FinalStatuses:
            payment.status = final_status
            payment.save()

            data = {
                'currency': 'DZD'
            }

            self.client.patch(
                url, json.dumps(data), content_type='application/json'
            )

            response = self.client.get(
                url, content_type='application/json'
            )

            assert response.status_code == status.HTTP_200_OK
            assert response.data.get('currency') == initial_currency

    def test_filters_is_overdue(self):
        today = datetime.now(pytz.utc).date()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)

        customer = CustomerFactory()

        payment_unpaid_overdue = PaymentFactory.create(
            customer=customer,
            due_date=yesterday,
            status=Payment.Status.Unpaid)
        payment_unpaied_not_due = PaymentFactory.create(
            customer=customer,
            due_date=tomorrow,
            status=Payment.Status.Unpaid)
        payment_paid_not_due = PaymentFactory.create(
            customer=payment_unpaid_overdue.customer,
            due_date=tomorrow,
            status=Payment.Status.Paid)
        payment_canceled = PaymentFactory.create(
            customer=customer,
            due_date=yesterday,
            status=Payment.Status.Canceled)

        url = reverse(
            'payment-list', kwargs={'customer_pk': customer.pk}
        )

        overdue_url = url + '?is_overdue=True'
        not_overdue_url = url + '?is_overdue=False'

        self.assert_get_data(overdue_url, [payment_unpaid_overdue])
        self.assert_get_data(not_overdue_url, [payment_unpaied_not_due,
                                               payment_paid_not_due,
                                               payment_canceled])

    def test_filter_visible(self):
        customer = CustomerFactory()

        payment_visible = PaymentFactory.create(
            customer=customer,
            visible=True)
        payment_not_visible = PaymentFactory.create(
            customer=customer,
            visible=False)

        url = reverse(
            'payment-list', kwargs={'customer_pk': customer.pk}
        )

        visible_url = url + '?visible=True'
        not_visible_url = url + '?visible=False'

        self.assert_get_data(visible_url, [payment_visible])
        self.assert_get_data(not_visible_url, [payment_not_visible])

    def test_filter_status(self):
        customer = CustomerFactory()

        payment_paid_status = PaymentFactory.create(
            customer=customer,
            status=Payment.Status.Paid)
        payment_canceled_status = PaymentFactory.create(
            customer=customer,
            status=Payment.Status.Canceled)

        url = reverse(
            'payment-list', kwargs={'customer_pk': customer.pk}
        )

        url_paid_only = url + '?status=' + Payment.Status.Paid
        url_canceled_only = url + '?status=' + Payment.Status.Canceled
        url_no_output = url + '?status=RANDOM'

        self.assert_get_data(url_paid_only, [payment_paid_status])
        self.assert_get_data(url_canceled_only, [payment_canceled_status])
        self.assert_get_data(url_no_output, [])

    def test_filter_flow(self):
        customer = CustomerFactory()

        payment_flow_invoice = PaymentFactory.create(
            customer=customer,
            provider__flow=Provider.FLOWS.INVOICE)
        payment_flow_proforma = PaymentFactory.create(
            customer=customer,
            provider__flow=Provider.FLOWS.PROFORMA)

        url = reverse(
            'payment-list', kwargs={'customer_pk': customer.pk}
        )

        invoice_url = url + '?flow=' + Provider.FLOWS.INVOICE
        proforma_url = url + '?flow=' + Provider.FLOWS.PROFORMA
        url_no_output = url + '?flow=RANDOM'

        self.assert_get_data(invoice_url, [payment_flow_invoice])
        self.assert_get_data(proforma_url, [payment_flow_proforma])
        self.assert_get_data(url_no_output, [])

    def test_filter_provider(self):
        customer = CustomerFactory()

        payment = PaymentFactory.create(
            customer=customer,
            provider__name='Gigel')

        url = reverse(
            'payment-list', kwargs={'customer_pk': customer.pk}
        )

        iexact_url = url + '?provider=gigel'
        exact_url = url + '?provider=Gigel'
        url_no_output = url + '?provider=RANDOM'

        self.assert_get_data(iexact_url, [payment])
        self.assert_get_data(exact_url, [payment])
        self.assert_get_data(url_no_output, [])

    def test_filters_min_max_amount(self):
        customer = CustomerFactory()

        payment_below_min = PaymentFactory.create(
            customer=customer,
            amount=9.99)
        payment_min = PaymentFactory.create(
            customer=customer,
            amount=10.00)
        payment_above_min = PaymentFactory.create(
            customer=customer,
            amount=10.01)
        payment_center = PaymentFactory.create(
            customer=customer,
            amount=60)
        payment_below_max = PaymentFactory.create(
            customer=customer,
            amount=99.99)
        payment_max = PaymentFactory.create(
            customer=customer,
            amount=100.00)
        payment_above_max = PaymentFactory.create(
            customer=customer,
            amount=100.01)

        url = reverse(
            'payment-list', kwargs={'customer_pk': customer.pk}
        )

        url_range_slice = url + '?min_amount=10&max_amount=100'
        url_range_all_entries = url + '?min_amount=9.99&max_amount=100.01'
        url_exact_amount = url + '?min_amount=60&max_amount=60'
        url_no_intersection = url + '?min_amount=100&max_amount=0'

        self.assert_get_data(url_range_slice, [payment_min,
                                               payment_above_min,
                                               payment_center,
                                               payment_below_max,
                                               payment_max])
        self.assert_get_data(url_range_all_entries, [payment_below_min,
                                                     payment_min,
                                                     payment_above_min,
                                                     payment_center,
                                                     payment_below_max,
                                                     payment_max,
                                                     payment_above_max])
        self.assert_get_data(url_exact_amount, [payment_center])
        self.assert_get_data(url_no_intersection, [])

    def test_filters_currency(self):
        customer = CustomerFactory()

        payment_usd = PaymentFactory.create(
            customer=customer,
            currency='USD')
        payment_std = PaymentFactory.create(
            customer=customer,
            currency='STD')

        url = reverse(
            'payment-list', kwargs={'customer_pk': customer.pk}
        )

        url_usd_iexact = url + '?currency=UsD'
        url_usd_exact = url + '?currency=USD'
        url_std = url + '?currency=STD'
        url_no_output = url + '?currency=RANDOM'

        self.assert_get_data(url_usd_iexact, [payment_usd])
        self.assert_get_data(url_usd_exact, [payment_usd])
        self.assert_get_data(url_std, [payment_std])
        self.assert_get_data(url_no_output, [])
