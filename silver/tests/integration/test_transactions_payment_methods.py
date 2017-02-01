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
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from silver.models import Invoice

from silver.tests.factories import (PaymentMethodFactory, InvoiceFactory,
                                    TransactionFactory)
from silver.tests.fixtures import (PAYMENT_PROCESSORS, triggered_processor)


@override_settings(PAYMENT_PROCESSORS=PAYMENT_PROCESSORS)
class TestDocumentsTransactions(TestCase):
    def test_create_transaction_with_not_allowed_currency(self):
        invoice = InvoiceFactory.create(transaction_currency='EUR',
                                        transaction_xe_rate=Decimal('1.0'),
                                        state=Invoice.STATES.ISSUED)
        payment_method = PaymentMethodFactory.create(
            payment_processor=triggered_processor,
            customer=invoice.customer,
            canceled=False,
            verified=True
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
