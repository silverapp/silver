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

from datetime import datetime, timedelta
from collections import OrderedDict
from decimal import Decimal

from mock import patch, MagicMock

from rest_framework import status
from rest_framework.reverse import reverse as _reverse
from rest_framework.test import APITestCase

from django.utils import timezone
from django.template.loader import render_to_string

from silver.models import Transaction
from silver.models.payment_processors.base import PaymentProcessorBase
from silver.models.payment_processors.mixins import TriggeredProcessorMixin
from silver.utils.payments import get_payment_url

from silver.tests.factories import (AdminUserFactory, TransactionFactory,
                                    PaymentMethodFactory, InvoiceFactory,
                                    ProformaFactory, CustomerFactory)
from silver.tests.utils import register_processor
from silver.utils.payments import get_payment_url, get_payment_complete_url


class TestPaymentUrls(APITestCase):
    def setUp(self):
        self.user = AdminUserFactory.create()
        self.client.force_authenticate(user=self.user)

    def test_pay_transaction_view_expired(self):
        transaction = TransactionFactory.create()

        with patch('silver.utils.payments.datetime') as mocked_datetime:
            mocked_datetime.utcnow.return_value = datetime.utcnow() - timedelta(days=365)
            url = get_payment_url(transaction, None)

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_pay_transaction_view_invalid_state(self):
        transaction = TransactionFactory.create(state=Transaction.States.Settled)

        response = self.client.get(get_payment_url(transaction, None))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content,
                         render_to_string('transactions/complete_payment.html', {
                             'expired': False,
                             'transaction': transaction,
                             'document': transaction.document,
                         }))

    def test_pay_transaction_view_not_consumable_transaction(self):
        last_year = timezone.now() - timedelta(days=365)
        transaction = TransactionFactory.create(state=Transaction.States.Initial,
                                                valid_until=last_year)

        response = self.client.get(get_payment_url(transaction, None))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_pay_transaction_view_missing_view(self):
        last_year = timezone.now() - timedelta(days=365)
        transaction = TransactionFactory.create(state=Transaction.States.Initial,
                                                valid_until=last_year)
        transaction.payment_processor.get_view = lambda transaction, request: None
        response = self.client.get(get_payment_url(transaction, None))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_pay_transaction_not_implemented_get_call(self):
        last_year = timezone.now() - timedelta(days=365)
        transaction = TransactionFactory.create(state=Transaction.States.Initial,
                                                valid_until=last_year)
        def view(*args):
            raise NotImplementedError

        transaction.payment_processor.get_view = lambda transaction, request: view
        response = self.client.get(get_payment_url(transaction, None))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


    def test_complete_payment_view_with_return_url(self):
        transaction = TransactionFactory.create(state=Transaction.States.Settled)

        return_url = 'http://home.com'
        complete_url = "{}?return_url={}".format(get_payment_complete_url(transaction, None),
                                                 return_url)
        expected_url = "{}?transaction_uuid={}".format(return_url,
                                                       transaction.uuid)

        response = self.client.get(complete_url, follow=False)
        self.assertRedirects(response, expected_url,
                             fetch_redirect_response=False)

    def test_complete_payment_view_without_return_url(self):
        transaction = TransactionFactory.create(state=Transaction.States.Settled)

        response = self.client.get(get_payment_complete_url(transaction, None))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content,
                         render_to_string('transactions/complete_payment.html', {
                             'expired': False,
                             'transaction': transaction,
                             'document': transaction.document,
                         }))
