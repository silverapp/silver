# Copyright (c) 2016 Presslabs SRL
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

from django.core.management.base import BaseCommand

from silver.models import PaymentProcessorManager
from silver.models import Transaction
from silver.models.payment_processors.mixins import PaymentProcessorTypes

logger = logging.getLogger(__name__)


def string_to_list(list_as_string):
    return list(map(int, list_as_string.strip('[] ').split(',')))


class Command(BaseCommand):
    help = 'Generates the billing documents (Invoices, Proformas).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--transactions',
            help='A list of transaction pks to be executed.',
            action='store', dest='transactions', type=string_to_list
        )

    def handle(self, *args, **options):
        payment_processors = [
            pp.reference for pp in PaymentProcessorManager.all_instances()
            if pp.type == PaymentProcessorTypes.Triggered
        ]

        executable_transactions = Transaction.objects.filter(
            state__in=[Transaction.States.Initial, Transaction.States.Pending],
            payment_method__payment_processor__in=payment_processors
        )

        if options['transactions']:
            executable_transactions = executable_transactions.filter(
                pk__in=options['transactions']
            )

        for transaction in executable_transactions:
            try:
                transaction.payment_processor.execute_transaction(transaction)
            except Exception:
                logger.error('Encountered exception while executing transaction '
                             'with id=%s.', transaction.id, exc_info=True)
