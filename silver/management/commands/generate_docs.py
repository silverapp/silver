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

import logging
import argparse

from datetime import datetime as dt

from django.core.management.base import BaseCommand
from django.utils import translation

from silver.documents_generator import DocumentsGenerator
from silver.models import Subscription


logger = logging.getLogger(__name__)


def date(date_str):
    try:
        return dt.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        msg = "Not a valid date: '{date_str}'. "\
              "Expected format: YYYY-MM-DD.".format(date_str=date_str)
        raise argparse.ArgumentTypeError(msg)


class Command(BaseCommand):
    help = 'Generates the billing documents (Invoices, Proformas).'

    def add_arguments(self, parser):
        parser.add_argument('--subscription',
                            action='store', dest='subscription_id', type=int,
                            help='The id of ths subscription to be billed.')
        parser.add_argument('--date',
                            action='store', dest='billing_date', type=date,
                            help='The billing date (format YYYY-MM-DD).')

    def handle(self, *args, **options):
        translation.activate('en-us')

        billing_date = options['billing_date']

        docs_generator = DocumentsGenerator()
        if options['subscription_id']:
            try:
                subscription_id = options['subscription_id']
                logger.info('Generating for subscription with id=%s; '
                            'billing_date=%s.', subscription_id,
                            billing_date)

                subscription = Subscription.objects.get(id=subscription_id)
                docs_generator.generate(subscription=subscription,
                                        billing_date=billing_date)
                self.stdout.write('Done. You can have a Club-Mate now. :)')
            except Subscription.DoesNotExist:
                msg = 'The subscription with the provided id does not exist.'
                self.stdout.write(msg)
        else:
            logger.info('Generating for all the available subscriptions; '
                        'billing_date=%s.', billing_date)

            docs_generator.generate(billing_date=billing_date)
            self.stdout.write('Done. You can have a Club-Mate now. :)')
