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

import logging

from six.moves import map

from django.core.management.base import BaseCommand

from silver import payment_processors
from silver.models import Transaction
from silver.payment_processors.mixins import PaymentProcessorTypes


logger = logging.getLogger(__name__)


def string_to_list(list_as_string):
    return list(map(int, list_as_string.strip('[] ').split(',')))


class Command(BaseCommand):
    help = 'Runs update_status on eligible transactions.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--transactions',
            help='A list of transaction pks to be updated.',
            action='store', dest='transactions', type=string_to_list
        )

    def handle(self, *args, **options):
        eligible_transactions = Transaction.objects.filter(
            state=Transaction.States.Pending,
        )

        if options['transactions']:
            eligible_transactions = eligible_transactions.filter(
                pk__in=options['transactions']
            )

        for transaction in eligible_transactions:
            try:
                payment_processor = transaction.payment_method.get_payment_processor()
                if payment_processor.type != PaymentProcessorTypes.Triggered:
                    continue
                payment_processor.fetch_transaction_status(transaction)
            except Exception:
                logger.error('Encountered exception while updating transaction '
                             'with id=%s.', transaction.id, exc_info=True)
