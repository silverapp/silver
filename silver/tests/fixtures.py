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

from silver.payment_processors import PaymentProcessorBase
from silver.payment_processors.mixins import (TriggeredProcessorMixin,
                                              ManualProcessorMixin)
from silver.payment_processors.views import GenericTransactionView

triggered_processor = 'triggered'
manual_processor = 'manual'
failing_void_processor = 'failing_void'

PAYMENT_PROCESSORS = {
    triggered_processor: {
        'class': 'silver.tests.fixtures.TriggeredProcessor'
    },
    manual_processor: {
        'class': 'silver.tests.fixtures.ManualProcessor'
    },
    failing_void_processor: {
        'class': 'silver.tests.fixtures.FailingVoidTriggeredProcessor'
    }

}


def not_implemented_view(*args):
    raise NotImplementedError


class ManualProcessor(PaymentProcessorBase, ManualProcessorMixin):
    transaction_view_class = GenericTransactionView


class TriggeredProcessor(PaymentProcessorBase, TriggeredProcessorMixin):
    transaction_view_class = GenericTransactionView

    def fetch_transaction_status(self, transaction):
        pass

    def execute_transaction(self, transaction):
        pass

    def void_transaction(self, transaction):
        transaction.cancel()
        return True

    @property
    def allowed_currencies(self):
        return ['RON', 'USD']


class FailingVoidTriggeredProcessor(TriggeredProcessor):
    def void_transaction(self, transaction):
        return False
