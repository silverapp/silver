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

import logging
import os

from django.contrib.admin.templatetags.admin_list import items_for_result
from django.utils.deconstruct import deconstructible

logger = logging.getLogger(__name__)


class PaymentProcessorTypes(object):
    Manual = "manual"
    Automatic = "automatic"
    Triggered = "triggered"


class ManualProcessorMixin(object):
    type = PaymentProcessorTypes.Manual


class BaseActionableProcessor(object):
    """
        Not a Manual type Processor
    """

    def refund_transaction(self, transaction, payment_method=None):
        """
            Refunds / returns the money to the given payment_method or to the
            transaction's payment method
        """

        raise NotImplementedError

    def void_transaction(self, transaction, payment_method=None):
        """
            Voids / interrupts an ongoing transaction
        """

        raise NotImplementedError

    def execute_transaction(self, transaction):
        """
            Only gets called for initial transactions that point to this
            specific Processor
        """

        raise NotImplementedError

    def update_transaction_status(self, transaction):
        """
            Only gets called for pending transactions that point to this
            specifc Processor
        """

        raise NotImplementedError


class AutomaticProcessorMixin(BaseActionableProcessor):
    type = PaymentProcessorTypes.Automatic

    def setup_automated_payments(self, customer):
        """
            Does the necessary operations to ensure payments are automatically
            processed by the processor service.
        """
        raise NotImplementedError


class TriggeredProcessorMixin(BaseActionableProcessor):
    type = PaymentProcessorTypes.Triggered
