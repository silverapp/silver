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
from datetime import timedelta, datetime, date

import pytz
from decimal import Decimal
from django.core.management.base import BaseCommand

from silver.models import Transaction, Invoice, BillingLog
from silver.tests.factories import (ProviderFactory, CustomerFactory, PlanFactory,
                                    SubscriptionFactory, MeteredFeatureFactory, TransactionFactory,
                                    DocumentEntryFactory, InvoiceFactory)
import random

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Creating entities for testing purposes'

    def handle(self, *args, **options):
        test_date = datetime(2017, 9, 11, 10, 56, 24, 898509, pytz.UTC)
        test_date = test_date + timedelta(-565)
        plan_names = ['Oxygen', 'Helium', 'Enterprise']
        customer_names = []
        currency = ['USD', 'RON']

        provider = ProviderFactory.create(company='Presslabs', name='Presslabs', flow='invoice',
                                          default_document_state='issued')
        for i in range(5):
            customer_names.append(CustomerFactory.create())

        for i in range(25):
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
                start_date=test_date.date() + timedelta(-20)
            )

            subscription.activate()
            subscription.save()

            BillingLog.objects.create(subscription=subscription, billing_date=test_date.date(),
                                      total=plan.amount,
                                      metered_features_billed_up_to=test_date.date(),
                                      plan_billed_up_to=test_date.date() + timedelta(10))
            BillingLog.objects.create(subscription=subscription, total=plan.amount,
                                      billing_date=test_date.date() + timedelta(10),
                                      metered_features_billed_up_to=test_date.date() + timedelta(5),
                                      plan_billed_up_to=test_date.date() + timedelta(10))
            BillingLog.objects.create(subscription=subscription, total=plan.amount,
                                      billing_date=test_date.date() + timedelta(15),
                                      metered_features_billed_up_to=test_date.date() +
                                      timedelta(20),
                                      plan_billed_up_to=test_date.date() + timedelta(11))

            entry = DocumentEntryFactory()
            InvoiceFactory.create(invoice_entries=[entry], issue_date=test_date.date())

            test_date = test_date + timedelta(-15)

        numbers = [1, 3, 5, 7, 10]
        number = [-30, -100, -80]
        for invoice in Invoice.objects.filter(issue_date__isnull=False)[:10]:
            invoice.issue_date = invoice.issue_date + timedelta(random.choice(number))
            invoice.paid_date = invoice.issue_date + timedelta(random.choice(numbers))
            invoice.state = Invoice.STATES.PAID
            invoice.save()

        for invoice in Invoice.objects.filter(issue_date__isnull=False)[11:25]:
            invoice.issue_date = invoice.issue_date + timedelta(random.choice(number))
            invoice.state = Invoice.STATES.ISSUED
            invoice.save()

            TransactionFactory.create(state=Transaction.States.Settled,
                                      invoice=invoice,
                                      payment_method__customer=invoice.customer,
                                      proforma=None,
                                      created_at=date(2017, 3, 6))
