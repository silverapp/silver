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
from django.test import override_settings

from silver.models.payment_processors.base import PaymentProcessorBase
from silver.models.payment_processors.mixins import TriggeredProcessorMixin
from silver.tests.factories import TransactionFactory, PaymentMethodFactory


class TriggeredProcessor(PaymentProcessorBase, TriggeredProcessorMixin):
    def manage_transaction(self, transaction):
        pass


PAYMENT_PROCESSORS = {
    'manual': {
        'path': 'silver.models.payment_processors.manual.ManualProcessor',
        'display_name': 'Manual'
    },
    'triggeredprocessor': {
        'path': 'silver.tests.commands.test_manage_transactions.TriggeredProcessor',
        'display_name': 'TriggeredProcessor'
    }
}


class TestInvoiceGenerationCommand(TestCase):
    @override_settings(PAYMENT_PROCESSORS=PAYMENT_PROCESSORS)
    def test_transaction_managing(self):
        payment_method = PaymentMethodFactory.create(
            payment_processor='triggeredprocessor'
        )
        transactions = TransactionFactory.create_batch(
            5, payment_method=payment_method
        )

        mock_manage = MagicMock()
        with patch.multiple(TriggeredProcessor,
                            manage_transaction=mock_manage):
            call_command('manage_transactions')

            for transaction in transactions:
                self.assertIn(call(transaction), mock_manage.call_args_list)

            self.assertEqual(mock_manage.call_count, len(transactions))

    @override_settings(PAYMENT_PROCESSORS=PAYMENT_PROCESSORS)
    def test_transaction_filtering(self):
        payment_method = PaymentMethodFactory.create(
            payment_processor='triggeredprocessor'
        )
        transactions = TransactionFactory.create_batch(
            5, payment_method=payment_method
        )

        filtered_transactions = [
            transactions[0], transactions[2], transactions[4]
        ]

        mock_manage = MagicMock()
        with patch.multiple(TriggeredProcessor,
                            manage_transaction=mock_manage):
            transactions_arg = [
                str(transaction.pk) for transaction in filtered_transactions
            ]
            call_command('manage_transactions',
                         '--transactions=%s' % ','.join(transactions_arg))

            for transaction in filtered_transactions:
                self.assertIn(call(transaction), mock_manage.call_args_list)

            self.assertEqual(mock_manage.call_count, len(filtered_transactions))

    @patch('silver.management.commands.manage_transactions.logger.error')
    @override_settings(PAYMENT_PROCESSORS=PAYMENT_PROCESSORS)
    def test_exception_logging(self, mock_logger):
        payment_method = PaymentMethodFactory.create(
            payment_processor='triggeredprocessor'
        )
        TransactionFactory.create(payment_method=payment_method)

        mock_manage = MagicMock()
        mock_manage.side_effect = Exception('This happened.')

        with patch.multiple(TriggeredProcessor,
                            manage_transaction=mock_manage):
            call_command('manage_transactions')
            expected_call = call(
                'Encountered exception while managing transaction with id=%s.',
                1, exc_info=True
            )
            self.assertEqual(expected_call, mock_logger.call_args)
