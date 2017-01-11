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

from mock import MagicMock, patch, call

from django.core.management import call_command
from django.test import TestCase
from silver.models import Transaction

from silver.models.payment_processors.base import PaymentProcessorBase
from silver.models.payment_processors.mixins import TriggeredProcessorMixin
from silver.tests.factories import TransactionFactory, PaymentMethodFactory
from silver.tests.utils import register_processor


class TriggeredProcessor(PaymentProcessorBase, TriggeredProcessorMixin):
    reference = 'triggeredprocessor'

    def update_transaction_status(self, transaction):
        pass


class TestUpdateTransactionsStatusCommand(TestCase):
    @register_processor(TriggeredProcessor, display_name='TriggeredProcessor')
    def test_update_transaction_status_call(self):
        payment_method = PaymentMethodFactory.create(
            payment_processor='triggeredprocessor'
        )
        transactions = TransactionFactory.create_batch(
            5, payment_method=payment_method, state=Transaction.States.Pending
        )

        mock_update_status = MagicMock()
        with patch.multiple(TriggeredProcessor,
                            update_transaction_status=mock_update_status):
            call_command('update_transactions_status')

            for transaction in transactions:
                self.assertIn(call(transaction),
                              mock_update_status.call_args_list)

            self.assertEqual(mock_update_status.call_count,
                             len(transactions))

    @register_processor(TriggeredProcessor, display_name='TriggeredProcessor')
    def test_update_transaction_status_transactions_filtering(self):
        payment_method = PaymentMethodFactory.create(
            payment_processor='triggeredprocessor'
        )
        transactions = TransactionFactory.create_batch(
            5, payment_method=payment_method, state=Transaction.States.Pending
        )

        filtered_transactions = [
            transactions[0], transactions[2], transactions[4]
        ]

        mock_update_status = MagicMock()
        with patch.multiple(TriggeredProcessor,
                            update_transaction_status=mock_update_status):
            transactions_arg = [
                str(transaction.pk) for transaction in filtered_transactions
            ]
            call_command('update_transactions_status',
                         '--transactions=%s' % ','.join(transactions_arg))

            for transaction in filtered_transactions:
                self.assertIn(call(transaction),
                              mock_update_status.call_args_list)

            self.assertEqual(mock_update_status.call_count,
                             len(filtered_transactions))

    @patch('silver.management.commands.update_transactions_status.logger.error')
    @register_processor(TriggeredProcessor, display_name='TriggeredProcessor')
    def test_transaction_update_status_exception_logging(self, mock_logger):
        payment_method = PaymentMethodFactory.create(
            payment_processor='triggeredprocessor'
        )
        TransactionFactory.create(payment_method=payment_method,
                                  state=Transaction.States.Pending)

        mock_update_status = MagicMock()
        mock_update_status.side_effect = Exception('This happened.')

        with patch.multiple(TriggeredProcessor,
                            update_transaction_status=mock_update_status):
            call_command('update_transactions_status')
            expected_call = call(
                'Encountered exception while updating transaction with id=%s.',
                1, exc_info=True
            )

            self.assertEqual(expected_call, mock_logger.call_args)
