# Copyright (c) 2016 University of Oxford
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

from decimal import Decimal
from mock import patch, PropertyMock, MagicMock

from annoying.functions import get_object_or_None

from django.core.management import call_command
from django.test import TestCase
from django.utils.six import StringIO

from silver.management.commands.generate_docs import date as generate_docs_date
from silver.models import (Proforma, DocumentEntry, Invoice, Subscription,
                           Customer, Plan)
from silver.tests.factories import (SubscriptionFactory, PlanFactory,
                                    MeteredFeatureFactory,
                                    MeteredFeatureUnitsLogFactory,
                                    CustomerFactory, ProviderFactory)


class TestGenerateDocsArguments(TestCase):

    """
    Quick tests to ensure that generate_docs parses any arguments
    correctly

    Tests:
        * pass in nothing
        * pass in date
        * pass in subscription id
        * pass in date and subscription id

        TODO: add missing test descriptions
    """

    def __init__(self, *args, **kwargs):
        super(TestGenerateDocsArguments, self).__init__(*args, **kwargs)
        self.output = StringIO()
        self.good_output = 'Done. You can have a Club-Mate now. :)\n'
        self.date_string = '2016-06-01'
        self.date = generate_docs_date(self.date_string)

    def setUp(self):
        # Setup simple subscription
        self.plan = PlanFactory.create(interval=Plan.INTERVALS.MONTH,
                                       interval_count=1, generate_after=120,
                                       enabled=True, amount=Decimal('200.00'),
                                       trial_period_days=0)

        self.subscription = SubscriptionFactory.create(plan=self.plan,
                                                       start_date=self.date)
        self.subscription.activate()
        self.subscription.save()

    def test_generate_docs_no_args(self):

        call_command('generate_docs', stdout=self.output)

        assert self.output.getvalue() == self.good_output

    def test_generate_docs_subscription_argparser(self):

        call_command(
            'generate_docs', '--subscription=%s' % self.subscription.id,
            stdout=self.output
            )

        assert self.output.getvalue() == self.good_output

    def test_generate_docs_subscription_options(self):

        call_command('generate_docs', subscription=self.subscription.id,
                     stdout=self.output)
        assert self.output.getvalue() == self.good_output

    def test_generate_docs_date_argparser(self):

        call_command('generate_docs', '--date=%s' % self.date_string,
                     stdout=self.output)

        assert self.output.getvalue() == self.good_output

    def test_generate_docs_date_options(self):

        call_command('generate_docs', billing_date=self.date,
                     stdout=self.output)

        assert self.output.getvalue() == self.good_output

    def test_generate_docs_date_sub_argparser(self):

        call_command('generate_docs',
                     '--date=%s' % self.date_string,
                     '--subscription=%s' % self.subscription.id,
                     stdout=self.output)

        assert self.output.getvalue() == self.good_output

    def test_generate_docs_date_sub_options(self):

        call_command('generate_docs',
                     billing_date=self.date,
                     subscription=self.subscription.id,
                     stdout=self.output)

        assert self.output.getvalue() == self.good_output
