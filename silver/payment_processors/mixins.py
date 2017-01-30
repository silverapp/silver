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

            :return: True on success, False on failure.
        """

        raise NotImplementedError

    def void_transaction(self, transaction, payment_method=None):
        """
            Voids / interrupts a pending / ongoing transaction

            :return: True on success, False on failure.
        """

        raise NotImplementedError

    def execute_transaction(self, transaction):
        """
            Creates a real transaction based on the given transaction.

            Should only be called for initial transactions that belong to the
            payment processor where this is implemented.

            :return: True on success, False on failure.
        """

        raise NotImplementedError

    def fetch_transaction_status(self, transaction):
        """
            Implementation is optional.

            Used for payment processors that do not provide webhooks and require
            interrogations initiated by us, to obtain the status of the
            transaction.

            Should only be called for pending transactions that belong to the
            payment processor where this is implemented.

            Can be called for all pending transactions by using the management
            command with the same name.

            :return: True on success, False on failure.
        """

        return True


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
