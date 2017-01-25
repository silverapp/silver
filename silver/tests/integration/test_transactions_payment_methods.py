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
import json

from django.core.exceptions import ValidationError
from django.test import TestCase
from silver.models import Invoice
from silver.models import PaymentProcessorManager

from silver.models.payment_processors.base import PaymentProcessorBase
from silver.models.payment_processors.mixins import TriggeredProcessorMixin
from silver.tests.factories import (PaymentMethodFactory, InvoiceFactory,
                                    TransactionFactory)
from silver.tests.utils import register_processor


class TriggeredProcessor(PaymentProcessorBase, TriggeredProcessorMixin):
    reference = 'triggeredprocessor'

    @property
    def allowed_currencies(self):
        return ['RON', 'USD']


class TestDocumentsTransactions(TestCase):
    @register_processor(TriggeredProcessor, display_name='TriggeredProcessor')
    def test_create_transaction_with_not_allowed_currency(self):
        payment_processor = PaymentProcessorManager.get_instance(
            TriggeredProcessor.reference
        )

        invoice = InvoiceFactory.create(transaction_currency='EUR',
                                        transaction_xe_rate=1,
                                        state=Invoice.STATES.ISSUED)
        payment_method = PaymentMethodFactory.create(
            payment_processor=payment_processor,
            customer=invoice.customer,
            enabled=True,
            verified=True,
        )

        expected_exception = ValidationError
        expected_message = '{\'__all__\': [u"Currency EUR is not allowed by ' \
                           'the payment method. Allowed currencies are ' \
                           '[\'RON\', \'USD\']."]}'

        try:
            TransactionFactory.create(payment_method=payment_method,
                                      invoice=invoice)
            self.fail('{} not raised.'.format(str(expected_exception)))
        except expected_exception as e:
            self.assertEqual(expected_message, str(e))
