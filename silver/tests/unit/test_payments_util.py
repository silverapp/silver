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

from datetime import datetime, timedelta
from mock import patch, MagicMock, call

from django.test import TestCase, override_settings

from silver.fixtures.factories import TransactionFactory
from silver.fixtures.test_fixtures import PAYMENT_PROCESSORS
from silver.utils.decorators import get_transaction_from_token
from silver.utils.payments import (get_payment_url, get_payment_complete_url,
                                   _get_jwt_token)


@override_settings(PAYMENT_PROCESSORS=PAYMENT_PROCESSORS)
class TestPaymentsUtilMethods(TestCase):
    def test_get_payment_url(self):
        transaction = TransactionFactory()

        expected_url = '/pay/token/'
        with patch('silver.utils.payments._get_jwt_token') as mocked_token:
            mocked_token.return_value = 'token'

            self.assertEqual(get_payment_url(transaction, None), expected_url)

            assert mocked_token.mock_calls == [call(transaction)]

    def test_get_payment_complete_url(self):
        transaction = TransactionFactory()

        expected_url = '/pay/token/complete?return_url=http://google.com'
        mocked_request = MagicMock(GET={'return_url': 'http://google.com'},
                                   versioning_scheme=None)
        mocked_request.build_absolute_uri.return_value = '/pay/token/complete'

        with patch('silver.utils.payments._get_jwt_token') as mocked_token:
            mocked_token.return_value = 'token'

            self.assertEqual(get_payment_complete_url(transaction, mocked_request),
                             expected_url)

            assert mocked_token.mock_calls == [call(transaction)]

    def test_get_transaction_from_token(self):
        transaction = TransactionFactory()

        mocked_view = MagicMock()
        token = _get_jwt_token(transaction)

        self.assertEqual(get_transaction_from_token(mocked_view)(None, token),
                         mocked_view())
        mocked_view.has_calls([call(None, transaction, False), call()])

    def test_get_transaction_from_expired_token(self):
        transaction = TransactionFactory()

        mocked_view = MagicMock()
        with patch('silver.utils.payments.datetime') as mocked_datetime:
            mocked_datetime.utcnow.return_value = datetime.utcnow() - timedelta(days=2 * 365)
            token = _get_jwt_token(transaction)

        self.assertEqual(get_transaction_from_token(mocked_view)(None, token),
                         mocked_view())
        mocked_view.has_calls([call(None, transaction, True), call()])
