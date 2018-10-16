# Copyright (c) 2015 Presslabs SRL
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

from mock import MagicMock, patch, call

from django.core.management import call_command
from django.test import TestCase, override_settings

from silver.tests.factories import TransactionFactory, PaymentMethodFactory
from silver.tests.fixtures import (TriggeredProcessor, PAYMENT_PROCESSORS,
                                   triggered_processor)


@override_settings(PAYMENT_PROCESSORS=PAYMENT_PROCESSORS)
class TestExecuteTransactionsCommand(TestCase):
    def test_transaction_executing(self):
        payment_method = PaymentMethodFactory.create(
            payment_processor=triggered_processor,
            verified=True
        )

        transactions = TransactionFactory.create_batch(
            5, payment_method=payment_method
        )

        mock_execute = MagicMock()
        with patch.multiple(TriggeredProcessor,
                            execute_transaction=mock_execute):
            call_command('execute_transactions')

            for transaction in transactions:
                self.assertIn(call(transaction), mock_execute.call_args_list)

            self.assertEqual(mock_execute.call_count, len(transactions))

    def test_transaction_filtering(self):
        payment_method = PaymentMethodFactory.create(
            payment_processor=triggered_processor,
            verified=True
        )

        transactions = TransactionFactory.create_batch(
            5, payment_method=payment_method
        )

        filtered_transactions = [
            transactions[0], transactions[2], transactions[4]
        ]

        mock_execute = MagicMock()
        with patch.multiple(TriggeredProcessor,
                            execute_transaction=mock_execute):
            transactions_arg = [
                str(transaction.pk) for transaction in filtered_transactions
            ]
            call_command('execute_transactions',
                         '--transactions=%s' % ','.join(transactions_arg))

            for transaction in filtered_transactions:
                self.assertIn(call(transaction), mock_execute.call_args_list)

            self.assertEqual(mock_execute.call_count, len(filtered_transactions))

    @patch('silver.management.commands.execute_transactions.logger.error')
    def test_exception_logging(self, mock_logger):
        payment_method = PaymentMethodFactory.create(
            payment_processor=triggered_processor,
            verified=True
        )

        TransactionFactory.create(payment_method=payment_method)

        mock_execute = MagicMock()
        mock_execute.side_effect = Exception('This happened.')

        with patch.multiple(TriggeredProcessor,
                            execute_transaction=mock_execute):
            call_command('execute_transactions')
            expected_call = call(
                'Encountered exception while executing transaction with id=%s.',
                1, exc_info=True
            )

            self.assertEqual(expected_call, mock_logger.call_args)

    def test_skip_transaction_with_unverified_payment_method(self):
        payment_method = PaymentMethodFactory.create(
            payment_processor=triggered_processor,
            verified=False
        )

        TransactionFactory.create(payment_method=payment_method)

        mock_execute = MagicMock()
        with patch.multiple(TriggeredProcessor,
                            execute_transaction=mock_execute):
            call_command('execute_transactions')

            self.assertEqual(mock_execute.call_count, 0)
