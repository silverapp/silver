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
from silver.models.documents.entries import OriginType

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
        parser.add_argument('--force',
                            action='store', dest='force_generate', type=bool,
                            help='Bill subscriptions even in situations when they would be skipped.')
        parser.add_argument('--only_entry_type',
                            action='store', dest='only_entry_type', type=str,
                            help='Specify entry origin type to only bill those type of entries. (e.g.: "mfs" or "plan")')

    def handle(self, *args, **options):
        translation.activate('en-us')

        billing_date = options['billing_date']
        force_generate = options.get('force_generate', False)
        only_entry_type = (options.get('only_entry_type') or "").lower()

        if only_entry_type in ["mf", "mfs", "metered_feature", "metered_features"]:
            only_entry_type = OriginType.MeteredFeature
        elif only_entry_type in ["plan", "plans", "amount", "base", "base_amount"]:
            only_entry_type = OriginType.Plan
        else:
            only_entry_type = None


        docs_generator = DocumentsGenerator()
        if options['subscription_id']:
            try:
                subscription_id = options['subscription_id']
                logger.info('Generating for subscription with id=%s; '
                            'billing_date=%s; force_generate=%s; only_entry_type=%s.',
                            subscription_id, billing_date, force_generate, only_entry_type)

                subscription = Subscription.objects.get(id=subscription_id)
                docs_generator.generate(
                    subscription=subscription,
                    billing_date=billing_date,
                    force_generate=force_generate,
                    only_entry_type=only_entry_type,
                )
                self.stdout.write('Done. You can have a Club-Mate now. :)')
            except Subscription.DoesNotExist:
                msg = 'The subscription with the provided id does not exist.'
                self.stdout.write(msg)
        else:
            logger.info('Generating for all the available subscriptions; '
                        'billing_date=%s; force_generate=%s; only_entry_type=%s.',
                        billing_date, force_generate, only_entry_type)

            docs_generator.generate(
                billing_date=billing_date,
                force_generate=force_generate,
                only_entry_type=only_entry_type,
            )
            self.stdout.write('Done. You can have a Club-Mate now. :)')
