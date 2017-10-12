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
from datetime import timedelta, datetime

import pytz
from decimal import Decimal
from django.core.management import call_command
from django.core.management.base import BaseCommand

from silver.models import Transaction, Invoice, BillingLog
from silver.tests.factories import (ProviderFactory, CustomerFactory, PlanFactory,
                                    SubscriptionFactory, MeteredFeatureFactory, TransactionFactory)
import random

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Creating entities for testing purposes'

    def handle(self, *args, **options):
        test_date = datetime(2017, 9, 11, 10, 56, 24, 898509, pytz.UTC)
        test_date = test_date + timedelta(-365)
        plan_names = ['Oxygen', 'Helium', 'Enterprise']
        customer_names = []
        currency = ['USD', 'RON']

        provider = ProviderFactory.create(company='Presslabs', name='Presslabs', flow='invoice',
                                          default_document_state='issued')
        for i in range(5):
            customer_names.append(CustomerFactory.create())

        for i in range(3):
            metered_feature = MeteredFeatureFactory(
                included_units_during_trial=Decimal('0.00'),
                price_per_unit=Decimal('2.5'))

            plan = PlanFactory.create(name=random.choice(plan_names),
                                      currency=random.choice(currency),
                                      provider=provider, generate_after=120,
                                      metered_features=[metered_feature])
            subscription = SubscriptionFactory.create(
                plan=plan,
                customer=random.choice(customer_names),
                start_date=test_date.date()
            )

            subscription.activate()
            subscription.save()

            BillingLog.objects.create(subscription=subscription, billing_date=test_date.date(),
                                      total=plan.amount)

            call_command('generate_docs',
                         '--date=%s' % test_date.date(),
                         '--subscription=%s' % subscription.id)

            test_date = test_date + timedelta(-15)

        numbers = [1, 3, 5, 7, 10]
        number = [-30, -100, -80]
        for invoice in Invoice.objects.all()[:10]:
            invoice.issue_date = invoice.issue_date + timedelta(random.choice(number))
            invoice.paid_date = invoice.issue_date + timedelta(random.choice(numbers))
            invoice.state = Invoice.STATES.PAID
            invoice.save()

        for invoice in Invoice.objects.all()[11:25]:
            invoice.issue_date = invoice.issue_date + timedelta(random.choice(number))
            invoice.state = Invoice.STATES.ISSUED
            invoice.save()

            TransactionFactory.create(state=Transaction.States.Settled,
                                      invoice=invoice,
                                      payment_method__customer=invoice.customer,
                                      proforma=None)
