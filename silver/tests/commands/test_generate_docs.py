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

import datetime as dt

from decimal import Decimal
from mock import patch, PropertyMock, MagicMock

from django.core.management import call_command
from django.test import TestCase
from django.utils.six import StringIO

from silver.management.commands.generate_docs import date as generate_docs_date
from silver.models import (Proforma, DocumentEntry, Invoice, Subscription, Customer, Plan,
                           BillingLog)
from silver.tests.factories import (SubscriptionFactory, PlanFactory,
                                    MeteredFeatureFactory,
                                    MeteredFeatureUnitsLogFactory,
                                    CustomerFactory, ProviderFactory)
from silver.utils.dates import ONE_DAY


class TestInvoiceGenerationCommand(TestCase):
    """
    Tests:
        * non-canceled
            * consolidated billing w/ included units --
            * consolidated billing w/a included units --
            * prorated subscriptions w/ consumed mfs underflow --
            * prorated subscriptions w/ consumed mfs overflow --
            * consolidated -> subscriptions full as well as full trial
            * non-consolidated billing w/ included units --
            * non-consolidated billing w/a included units --
            * non-consolidated billing w/ prorated subscriptions
            * Generate with different default states
                * draft --
                * issued --
            * trial over multiple months --
            * variations for non-canceled subscriptions. Check the cases paper --
        * canceled
            * canceled subscription w/ trial --
            * canceled subscription w/a trial --
            * canceled subscription w trial underflow --
            * canceled subscription w trial overflow --
        * dates -- with the current tests we only test value. The tests should
            should include the dates for the items too.
        * sales tax percent
        * generate_after

        TODO: add missing test descriptions
    """

    def __init__(self, *args, **kwargs):
        super(TestInvoiceGenerationCommand, self).__init__(*args, **kwargs)
        self.output = StringIO()

    ###########################################################################
    # Non-Canceled
    ###########################################################################
    def test_trial_spanning_over_multiple_months(self):
        # # SETUP ##
        customer = CustomerFactory.create(sales_tax_percent=Decimal('0.00'))

        mf_price = Decimal('2.5')
        metered_feature = MeteredFeatureFactory(
            included_units_during_trial=Decimal('0.00'),
            price_per_unit=mf_price)
        currency = 'EUR'
        plan = PlanFactory.create(interval=Plan.INTERVALS.MONTH,
                                  interval_count=1, generate_after=120,
                                  enabled=True, amount=Decimal('200.00'),
                                  trial_period_days=24,
                                  metered_features=[metered_feature],
                                  currency=currency)
        start_date = dt.date(2015, 5, 20)

        # Create the prorated subscription
        subscription = SubscriptionFactory.create(
            plan=plan, start_date=start_date, customer=customer)
        subscription.activate()
        subscription.save()

        consumed_1 = Decimal('5.00')
        consumed_2 = Decimal('5.00')
        mf_log = MeteredFeatureUnitsLogFactory.create(
            subscription=subscription, metered_feature=metered_feature,
            start_date=dt.date(2015, 6, 1), end_date=subscription.trial_end,
            consumed_units=consumed_1)

        prev_billing_date = generate_docs_date('2015-06-04')  # During trial period
        curr_billing_date = subscription.trial_end + ONE_DAY

        # # TEST ##
        call_command('generate_docs', billing_date=prev_billing_date, stdout=self.output)

        proforma = Proforma.objects.first()
        # Expect 4 entries:
        # - prorated plan trial (+-) first month
        # - prorated plan trial (+-) next month
        assert proforma.proforma_entries.count() == 4

        assert Invoice.objects.all().count() == 0

        assert Proforma.objects.all()[0].total == Decimal('0.00')

        mf_log.consumed_units += consumed_2
        mf_log.save()

        call_command('generate_docs', billing_date=curr_billing_date, stdout=self.output)

        assert Proforma.objects.all().count() == 2
        assert Invoice.objects.all().count() == 0

        proforma = Proforma.objects.all()[1]
        # Expect 2 entries:
        # - consumed mfs from trial (as included_during_trial=0)
        # - prorated subscription for the remaining period
        assert proforma.proforma_entries.count() == 2
        assert all([entry.prorated
                    for entry in proforma.proforma_entries.all()])
        assert all([entry.total != Decimal('0.0000')
                    for entry in proforma.proforma_entries.all()])
        prorated_plan_value = Decimal(18 / 30.0).quantize(Decimal('0.0000')) * plan.amount
        consumed_mfs_value = (consumed_1 + consumed_2) * mf_price
        assert proforma.total == prorated_plan_value + consumed_mfs_value
        assert proforma.currency == currency

    def test_gen_for_non_consolidated_billing_with_consumed_units(self):
        """
        A customer  has 3 subscriptions for which we use the normal case:
            * add consumed mfs for the previous month
            * add the value of the plan for the next month
            => 3 different proformas
        """
        billing_date = generate_docs_date('2015-03-01')

        customer = CustomerFactory.create(consolidated_billing=False)
        metered_feature = MeteredFeatureFactory(included_units=Decimal('0.00'))
        plan_price = Decimal('200.00')
        currency = 'RON'
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  amount=plan_price,
                                  metered_features=[metered_feature],
                                  currency=currency)
        start_date = dt.date(2014, 1, 1)

        # Create 3 subscriptions for the same customer
        SubscriptionFactory.create_batch(size=3,
                                         plan=plan, start_date=start_date,
                                         customer=customer)

        consumed_mfs = Decimal('50.00')
        for subscription in Subscription.objects.all():
            subscription.activate()
            subscription.save()

            # For each subscription, add consumed units
            MeteredFeatureUnitsLogFactory.create(
                subscription=subscription,
                metered_feature=metered_feature,
                start_date=dt.date(2015, 2, 1),
                end_date=dt.date(2015, 2, 28),
                consumed_units=consumed_mfs)

            # Add a BillingLog to declare when the subscription was last billed
            BillingLog.objects.create(subscription=subscription,
                                      billing_date=dt.date(2015, 1, 1),
                                      plan_billed_up_to=dt.date(2015, 2, 28),
                                      metered_features_billed_up_to=dt.date(2015, 1, 31))

        call_command('generate_docs', billing_date=billing_date,
                     stdout=self.output)

        assert Proforma.objects.all().count() == 3
        assert Invoice.objects.all().count() == 0

        for proforma in Proforma.objects.all():
            entries = proforma.proforma_entries.all()
            assert entries.count() == 2  # Plan for current month, Metered features for last month
            assert proforma.currency == currency

            for entry in entries:
                if entry.product_code == plan.product_code:
                    assert entry.quantity == 1
                    assert entry.unit_price == plan_price
                else:
                    assert entry.quantity == consumed_mfs
                    assert entry.unit_price == metered_feature.price_per_unit

    def test_gen_for_non_consolidated_billing_without_consumed_units(self):
        """
        A customer  has 3 subscriptions for which he does not have any
        consumed units => 3 different proformas, each containing only the
        plan's value.
        """
        billing_date = generate_docs_date('2015-03-01')

        customer = CustomerFactory.create(consolidated_billing=False)
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  amount=Decimal('200.00'))
        start_date = dt.date(2015, 1, 1)

        # Create 3 subscriptions for the same customer
        SubscriptionFactory.create_batch(
            size=3, plan=plan, start_date=start_date, customer=customer)

        for subscription in Subscription.objects.all():
            subscription.activate()
            subscription.save()

        call_command('generate_docs', billing_date=billing_date,
                     stdout=self.output)

        assert Proforma.objects.all().count() == 3
        assert Invoice.objects.all().count() == 0

        for proforma in Proforma.objects.all():
            entries = proforma.proforma_entries.all()
            # plan for january
            # plan for february
            # plan for march
            assert entries.count() == 3
            assert proforma.currency == 'USD'

            for entry in entries:
                assert entry.quantity == 1
                assert entry.unit_price == plan.amount

    def test_gen_consolidated_billing_with_consumed_mfs(self):
        """
        A customer has 3 subscriptions for which we use the normal case:
            * add consumed mfs for the previous month for each subscription
            * add the value of the plan for the next month for each subscription
            => 1 proforma with all the aforementioned data
        """

        billing_date = generate_docs_date('2015-03-01')
        subscriptions_cnt = 3

        customer = CustomerFactory.create(
            consolidated_billing=True,
            sales_tax_percent=Decimal('0.00'))
        mf_price = Decimal('2.5')
        metered_feature = MeteredFeatureFactory(
            included_units=Decimal('0.00'), price_per_unit=mf_price)
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  amount=Decimal('200.00'),
                                  metered_features=[metered_feature])
        start_date = dt.date(2014, 1, 3)

        subscriptions = SubscriptionFactory.create_batch(
            size=subscriptions_cnt, plan=plan, start_date=start_date,
            customer=customer)

        consumed_mfs = Decimal('50.00')
        for subscription in subscriptions:
            subscription.activate()
            subscription.save()

            # For each subscription, add consumed units
            MeteredFeatureUnitsLogFactory.create(
                subscription=subscription,
                metered_feature=metered_feature,
                start_date=dt.date(2015, 2, 1),
                end_date=dt.date(2015, 2, 28),
                consumed_units=consumed_mfs)

            BillingLog.objects.create(subscription=subscription,
                                      billing_date=dt.date(2015, 2, 1),
                                      plan_billed_up_to=dt.date(2015, 2, 28),
                                      metered_features_billed_up_to=dt.date(2015, 1, 31))

        call_command('generate_docs', billing_date=billing_date, stdout=self.output)

        assert Proforma.objects.all().count() == 1
        assert Invoice.objects.all().count() == 0

        proforma = Proforma.objects.all()[0]
        # For each doc, expect 2 entries: the plan value and the mfs
        assert proforma.proforma_entries.all().count() == subscriptions_cnt * 2

        expected_total = (subscriptions_cnt * plan.amount +
                          subscriptions_cnt * (mf_price * consumed_mfs))
        assert proforma.total == expected_total

    def test_gen_consolidated_billing_without_mfs(self):
        """
        A customer has 3 subscriptions for which it does not have any
        consumed metered features.
        """

        billing_date = generate_docs_date('2015-03-01')
        subscriptions_cnt = 3

        customer = CustomerFactory.create(
            consolidated_billing=True,
            sales_tax_percent=Decimal('0.00'))
        mf_price = Decimal('2.5')
        metered_feature = MeteredFeatureFactory(
            included_units=Decimal('0.00'), price_per_unit=mf_price)
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  amount=Decimal('200.00'),
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 1, 3)

        subscriptions = SubscriptionFactory.create_batch(
            size=subscriptions_cnt, plan=plan, start_date=start_date, customer=customer
        )

        for subscription in subscriptions:
            subscription.activate()
            subscription.save()

            BillingLog.objects.create(subscription=subscription,
                                      billing_date=dt.date(2015, 2, 1),
                                      plan_billed_up_to=dt.date(2015, 2, 28),
                                      metered_features_billed_up_to=dt.date(2015, 1, 31))

        call_command('generate_docs', billing_date=billing_date, stdout=self.output)

        assert Proforma.objects.all().count() == 1
        assert Invoice.objects.all().count() == 0

        proforma = Proforma.objects.all()[0]
        # For each doc, expect 2 entries: the plan's value + the 'extra'
        # mfs with 0 value
        assert proforma.proforma_entries.all().count() == 2 * subscriptions_cnt

        expected_total = subscriptions_cnt * plan.amount
        assert proforma.total == expected_total

    def test_prorated_subscription_with_consumed_mfs_underflow(self):
        """
        The subscription started last month and it does not have a trial
        => prorated value for the plan; the consumed_mfs < included_mfs
        => 1 proforma with 1 single value, corresponding to the plan for the
        next month
        """

        prev_billing_date = generate_docs_date('2015-02-14')
        curr_billing_date = generate_docs_date('2015-03-02')

        customer = CustomerFactory.create(
            consolidated_billing=False, sales_tax_percent=Decimal('0.00'))
        metered_feature = MeteredFeatureFactory(included_units=Decimal('20.00'))
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  amount=Decimal('200.00'),
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 2, 14)

        # Create the prorated subscription
        subscription = SubscriptionFactory.create(
            plan=plan, start_date=start_date, customer=customer, trial_end=None)
        subscription.activate()
        subscription.save()

        call_command('generate_docs', date=prev_billing_date,
                     stdout=self.output)

        assert Proforma.objects.all().count() == 1
        assert Invoice.objects.all().count() == 0

        MeteredFeatureUnitsLogFactory.create(
            subscription=subscription, metered_feature=metered_feature,
            start_date=dt.date(2015, 2, 14), end_date=dt.date(2015, 2, 28),
            consumed_units=Decimal('10.00'))

        call_command('generate_docs', date=curr_billing_date,
                     stdout=self.output)

        assert Proforma.objects.all().count() == 2
        assert Invoice.objects.all().count() == 0

        proforma = Proforma.objects.all()[1]
        # Expect 2 entries: the plan for the next month and the consumed mfs with 0 total.
        assert proforma.proforma_entries.all().count() == 2
        assert proforma.total == plan.amount

    def test_prorated_subscription_with_consumed_mfs_overflow(self):
        prev_billing_date = generate_docs_date('2015-02-15')
        curr_billing_date = generate_docs_date('2015-03-02')

        customer = CustomerFactory.create(consolidated_billing=False,
                                          sales_tax_percent=Decimal('0.00'))

        mf_price = Decimal('2.5')
        metered_feature = MeteredFeatureFactory(included_units=Decimal('20.00'),
                                                price_per_unit=mf_price)
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  amount=Decimal('200.00'),
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 2, 15)

        # Create the prorated subscription
        subscription = SubscriptionFactory.create(
            plan=plan, start_date=start_date, customer=customer)
        subscription.activate()
        subscription.save()

        call_command('generate_docs', date=prev_billing_date, stdout=self.output)

        assert Proforma.objects.all().count() == 1
        assert Invoice.objects.all().count() == 0

        proforma = Proforma.objects.all()[0]
        assert proforma.total == Decimal(14 / 28.0) * plan.amount
        assert all([entry.prorated
                    for entry in proforma.proforma_entries.all()])

        MeteredFeatureUnitsLogFactory.create(
            subscription=subscription, metered_feature=metered_feature,
            start_date=dt.date(2015, 2, 15), end_date=dt.date(2015, 2, 28),
            consumed_units=Decimal('12.00'))

        call_command('generate_docs', date=curr_billing_date, stdout=self.output)

        assert Proforma.objects.all().count() == 2
        assert Invoice.objects.all().count() == 0

        proforma = Proforma.objects.all()[1]
        # Expect 2 entries: the plan for the next month + the extra consumed
        # units. extra_mfs = 2, since included_mfs=20 but the plan is
        # 50% prorated => only 50% of the total included_mfs are included.
        # The mfs will not be added as the consumed_mfs < included_mfs
        assert proforma.proforma_entries.all().count() == 2
        assert proforma.total == plan.amount + mf_price * 2
        # mfs for last month
        assert proforma.proforma_entries.all()[0].prorated is True
        # plan for upcoming month
        assert proforma.proforma_entries.all()[1].prorated is False

    def test_subscription_with_trial_without_metered_features_to_draft(self):
        billing_date = generate_docs_date('2015-03-02')

        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  trial_period_days=14, amount=Decimal('200.00'))

        start_date = dt.date(2015, 2, 4)

        subscription = SubscriptionFactory.create(plan=plan, start_date=start_date)
        subscription.activate()
        subscription.save()

        Customer.objects.all()[0].sales_tax_percent = Decimal('0.00')

        call_command('generate_docs', billing_date=billing_date, stdout=self.output)

        # Expect one Proforma
        assert Proforma.objects.all().count() == 1
        assert Invoice.objects.all().count() == 0

        # In draft state
        assert Proforma.objects.all()[0].state == Proforma.STATES.DRAFT

        document_entries = DocumentEntry.objects.all()
        # Expect 4 entries:
        # Plan Trial (+-), Plan Prorated (+), Plan for next month(+)
        assert len(document_entries) == 4

        doc = document_entries[0]
        assert doc.unit_price == Decimal(14.0 / 28).quantize(Decimal('0.0000')) * plan.amount

        doc = document_entries[1]
        assert doc.unit_price == - Decimal(14.0 / 28).quantize(Decimal('0.0000')) * plan.amount

        doc = document_entries[2]
        assert doc.unit_price == Decimal(11.0 / 28).quantize(Decimal('0.0000')) * plan.amount

        doc = document_entries[3]
        assert doc.unit_price == plan.amount

        # And quantity 1
        assert doc.quantity == 1

    def test_subscription_with_trial_with_metered_features_underflow_to_draft(self):
        included_units_during_trial = Decimal('5.00')
        metered_feature = MeteredFeatureFactory(
            included_units=Decimal('0.00'),
            included_units_during_trial=included_units_during_trial
        )
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  trial_period_days=7, amount=Decimal('200.00'),
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 2, 1)

        subscription = SubscriptionFactory.create(plan=plan, start_date=start_date)
        subscription.activate()
        subscription.save()

        consumed_mfs_during_trial = Decimal('3.00')
        MeteredFeatureUnitsLogFactory.create(
            subscription=subscription, metered_feature=metered_feature,
            start_date=start_date, end_date=subscription.trial_end,
            consumed_units=consumed_mfs_during_trial
        )

        mf_units_log_after_trial = MeteredFeatureUnitsLogFactory.create(
            subscription=subscription, metered_feature=metered_feature,
            start_date=subscription.trial_end + dt.timedelta(days=1),
            end_date=dt.datetime(2015, 2, 28)
        )

        call_command('generate_docs', billing_date=dt.date(2015, 3, 1), stdout=self.output)

        # Expect one Proforma
        assert Proforma.objects.all().count() == 1
        assert Invoice.objects.all().count() == 0

        # In draft state
        proforma = Proforma.objects.all()[0]
        assert proforma.state == Proforma.STATES.DRAFT

        document_entries = proforma.proforma_entries.all()
        # Expect 7 entries:
        # Plan Trial (+-), Plan Trial Metered Feature (+-), Plan After Trial (+)
        # Metered Features After Trial (+), Plan for next month (+)
        assert len(document_entries) == 7

        doc = document_entries[0]
        assert doc.unit_price == Decimal('50.00')  # 7 / 28 * 200

        doc = document_entries[1]
        assert doc.unit_price == Decimal('-50.00')

        doc = document_entries[2]
        assert doc.unit_price == metered_feature.price_per_unit
        assert doc.quantity == consumed_mfs_during_trial

        doc = document_entries[3]
        assert doc.unit_price == - metered_feature.price_per_unit
        assert doc.quantity == consumed_mfs_during_trial

        doc = document_entries[4]
        assert doc.unit_price == Decimal('150.00')  # 21 / 28 * 200

        doc = document_entries[5]
        assert doc.unit_price == metered_feature.price_per_unit
        assert doc.quantity == mf_units_log_after_trial.consumed_units

        doc = document_entries[6]
        assert doc.unit_price == plan.amount

        # And quantity 1
        assert doc.quantity == 1

    def test_subscription_with_trial_with_metered_features_overflow_to_draft(self):
        billing_date = generate_docs_date('2015-03-01')

        metered_feature = MeteredFeatureFactory(
            included_units=Decimal('0.00'),
            included_units_during_trial=Decimal('5.00'))
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  trial_period_days=7, amount=Decimal('200.00'),
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 2, 1)
        trial_end = start_date + dt.timedelta(days=plan.trial_period_days)

        subscription = SubscriptionFactory.create(
            plan=plan, start_date=start_date, trial_end=trial_end)
        subscription.activate()
        subscription.save()

        units_consumed_during_trial = Decimal('7.00')
        MeteredFeatureUnitsLogFactory(
            subscription=subscription, metered_feature=metered_feature,
            start_date=start_date, end_date=trial_end,
            consumed_units=units_consumed_during_trial
        )

        mf_units_log_after_trial = MeteredFeatureUnitsLogFactory(
            subscription=subscription, metered_feature=metered_feature,
            start_date=trial_end + dt.timedelta(days=1),
            end_date=dt.datetime(2015, 2, 28)
        )

        call_command('generate_docs', billing_date=billing_date,
                     stdout=self.output)

        # Expect one Proforma
        assert Proforma.objects.all().count() == 1
        assert Invoice.objects.all().count() == 0

        # In draft state
        assert Proforma.objects.all()[0].state == Proforma.STATES.DRAFT

        document_entries = DocumentEntry.objects.all()
        # Expect 7 entries:
        # Plan Trial (+-), Plan Trial Metered Feature (+-),
        # Extra units consumed during trial (+)
        # Plan After Trial (+)
        # Metered Features After Trial (+), Plan for next month (+)
        assert len(document_entries) == 8

        doc = document_entries[0]
        assert doc.unit_price == Decimal('57.14')

        doc = document_entries[1]
        assert doc.unit_price == Decimal('-57.14')

        doc = document_entries[2]
        assert doc.unit_price == metered_feature.price_per_unit
        assert doc.quantity == metered_feature.included_units_during_trial

        doc = document_entries[3]
        assert doc.unit_price == - metered_feature.price_per_unit
        assert doc.quantity == metered_feature.included_units_during_trial

        doc = document_entries[4]
        assert doc.unit_price == metered_feature.price_per_unit

        included_trial_units = metered_feature.included_units_during_trial
        assert doc.quantity == units_consumed_during_trial - included_trial_units

        doc = document_entries[5]
        assert doc.unit_price == Decimal('142.8600')  # 20 / 28 * 200

        doc = document_entries[6]
        assert doc.unit_price == metered_feature.price_per_unit
        assert doc.quantity == mf_units_log_after_trial.consumed_units

        doc = document_entries[7]
        assert doc.unit_price == Decimal('200.00')

        # And quantity 1
        assert doc.quantity == 1

    def test_on_trial_with_consumed_units_underflow(self):
        customer = CustomerFactory.create(sales_tax_percent=Decimal('0.00'))

        metered_feature = MeteredFeatureFactory(
            included_units_during_trial=Decimal('10.00'))
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  amount=Decimal('200.00'),
                                  trial_period_days=14,
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 2, 20)

        # Create the prorated subscription
        subscription = SubscriptionFactory.create(
            plan=plan, start_date=start_date, customer=customer)
        subscription.activate()
        subscription.save()
        MeteredFeatureUnitsLogFactory.create(
            subscription=subscription, metered_feature=metered_feature,
            start_date=dt.date(2015, 2, 20), end_date=dt.date(2015, 2, 28),
            consumed_units=Decimal('8.00'))

        billing_date = generate_docs_date('2015-03-02')
        call_command('generate_docs', billing_date=billing_date, stdout=self.output)

        assert Proforma.objects.all().count() == 1
        assert Invoice.objects.all().count() == 0

        proforma = Proforma.objects.all()[0]
        # Expect 6 entries:
        # - plan trial february (+-)
        # - mfs trial february (+-)
        # - plan trial march (+-)
        assert proforma.proforma_entries.count() == 6
        assert all([entry.prorated
                    for entry in proforma.proforma_entries.all()])
        assert all([entry.total != Decimal('0.0000')
                    for entry in proforma.proforma_entries.all()])
        assert proforma.total == Decimal('0.0000')

        billing_date = generate_docs_date('2015-03-07')

        call_command('generate_docs', billing_date=billing_date,
                     stdout=self.output)

        assert Proforma.objects.all().count() == 2
        assert Invoice.objects.all().count() == 0

        proforma = Proforma.objects.all()[1]
        # Expect 3 entries:
        # - mfs trial march (+-)
        # - remaining plan march (+)
        assert all([entry.prorated
                    for entry in proforma.proforma_entries.all()])
        assert all([entry.total != Decimal('0.0000')
                    for entry in proforma.proforma_entries.all()])
        assert proforma.total != Decimal('0.0000')

    def test_on_trial_with_consumed_units_overflow(self):
        billing_date = generate_docs_date('2015-03-07')

        customer = CustomerFactory.create(sales_tax_percent=Decimal('0.00'))

        mf_price = Decimal('2.5')
        included_during_trial = Decimal('10.00')
        metered_feature = MeteredFeatureFactory(
            included_units_during_trial=included_during_trial,
            price_per_unit=mf_price)
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  amount=Decimal('200.00'), trial_period_days=14,
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 2, 20)

        # Create the prorated subscription
        subscription = SubscriptionFactory.create(
            plan=plan, start_date=start_date, customer=customer)
        subscription.activate()
        subscription.save()
        consumed_during_trial = Decimal('12.00')
        MeteredFeatureUnitsLogFactory.create(
            subscription=subscription, metered_feature=metered_feature,
            start_date=dt.date(2015, 2, 20), end_date=dt.date(2015, 2, 28),
            consumed_units=consumed_during_trial)

        call_command('generate_docs', billing_date=billing_date, stdout=self.output)

        assert Proforma.objects.all().count() == 1
        assert Invoice.objects.all().count() == 0

        proforma = Proforma.objects.all()[0]
        # Expect 8 entries:
        # - plan trial february (+-)
        # - mfs trial february (+-)
        # - extra consumed mfs february (+)
        # - plan trial march (+-)
        # - remaining plan march (+)
        assert proforma.proforma_entries.count() == 8
        assert all([entry.prorated
                    for entry in proforma.proforma_entries.all()])
        assert all([entry.total != Decimal('0.0000')
                    for entry in proforma.proforma_entries.all()])
        extra_during_trial = consumed_during_trial - included_during_trial
        prorated_plan_value = Decimal(26 / 31.0).quantize(Decimal('0.0000')) * plan.amount
        assert proforma.total == extra_during_trial * mf_price + prorated_plan_value

    def test_2nd_sub_after_trial_with_consumed_units_underflow(self):
        """
        The subscription:
            * start_date=2015-05-20
            * trial_end=2015-06-03
            * first billing_date=2015-06-01
            * second billing_date=2015-06-04 (right after the trial_end)
        The consumed_during_trial < included_during_trial
        """

        # # SETUP ##
        prev_billing_date = generate_docs_date('2015-06-01')
        curr_billing_date = generate_docs_date('2015-06-04')  # First day after trial_end

        customer = CustomerFactory.create(sales_tax_percent=Decimal('0.00'))

        included_during_trial = Decimal('10.00')
        metered_feature = MeteredFeatureFactory(
            included_units_during_trial=included_during_trial)
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  amount=Decimal('200.00'), trial_period_days=14,
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 5, 20)

        # Create the prorated subscription
        subscription = SubscriptionFactory.create(
            plan=plan, start_date=start_date, customer=customer)
        subscription.activate()
        subscription.save()
        consumed_during_first_trial_part = Decimal('5.00')
        consumed_during_second_trial_part = Decimal('5.00')
        MeteredFeatureUnitsLogFactory.create(
            subscription=subscription, metered_feature=metered_feature,
            start_date=dt.date(2015, 5, 20), end_date=dt.date(2015, 5, 31),
            consumed_units=consumed_during_first_trial_part)
        MeteredFeatureUnitsLogFactory.create(
            subscription=subscription, metered_feature=metered_feature,
            start_date=dt.date(2015, 6, 1), end_date=dt.date(2015, 6, 2),
            consumed_units=consumed_during_second_trial_part)

        # # TEST ##
        call_command('generate_docs', billing_date=prev_billing_date,
                     stdout=self.output)

        assert Proforma.objects.all().count() == 1
        assert Invoice.objects.all().count() == 0
        proforma = Proforma.objects.first()
        # Expect 6 entries:
        # - plan trial may (+-)
        # - mfs trial may (+-)
        # - plan trial june (+-)
        assert proforma.proforma_entries.count() == 6
        assert all([entry.prorated
                    for entry in proforma.proforma_entries.all()])
        assert all([entry.total != Decimal('0.0000')
                    for entry in proforma.proforma_entries.all()])
        call_command('generate_docs', billing_date=curr_billing_date, stdout=self.output)
        assert proforma.total == Decimal('0.0000')

        call_command('generate_docs', billing_date=curr_billing_date,
                     stdout=self.output)

        assert Proforma.objects.all().count() == 2
        assert Invoice.objects.all().count() == 0

        proforma = Proforma.objects.all()[1]
        # Expect 3 entries:
        # - mfs trial june (+-)
        # - remaining plan june (+)
        assert proforma.proforma_entries.count() == 3
        for entry in proforma.proforma_entries.all():
            assert entry.prorated
            if entry.product_code == plan.product_code:
                assert entry.start_date == subscription.trial_end + ONE_DAY
                assert entry.end_date == dt.date(2015, 6, 30)
            else:
                assert entry.start_date == dt.date(2015, 6, 1)
                assert entry.end_date == subscription.trial_end

        assert proforma.total == Decimal(28 / 30.0).quantize(Decimal('0.0000')) * plan.amount

    def test_2nd_sub_billing_after_trial_with_all_consumed_units_overflow(self):
        """
        The subscription:
            * start_date=2015-05-20
            * trial_end=2015-06-03
            * first billing_date=2015-06-01
            * second billing_date=2015-06-04 (right after the trial_end)
        During 2014-05-20->2015-06-03 all the included_during_trial units have
        been consumed.
        """

        # # SETUP ##
        prev_billing_date = generate_docs_date('2015-06-01')
        curr_billing_date = generate_docs_date('2015-06-04')  # First day after trial_end

        customer = CustomerFactory.create(sales_tax_percent=Decimal('0.00'))

        included_during_trial = Decimal('10.00')
        mf_price = Decimal('2.5')
        metered_feature = MeteredFeatureFactory(
            included_units_during_trial=included_during_trial,
            price_per_unit=mf_price)
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  amount=Decimal('200.00'), trial_period_days=14,
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 5, 20)

        # Create the prorated subscription
        subscription = SubscriptionFactory.create(
            plan=plan, start_date=start_date, customer=customer)
        subscription.activate()
        subscription.save()
        consumed_during_first_trial_part = Decimal('10.00')
        consumed_during_second_trial_part = Decimal('12.00')
        MeteredFeatureUnitsLogFactory.create(
            subscription=subscription, metered_feature=metered_feature,
            start_date=dt.date(2015, 5, 20), end_date=dt.date(2015, 5, 31),
            consumed_units=consumed_during_first_trial_part)
        MeteredFeatureUnitsLogFactory.create(
            subscription=subscription, metered_feature=metered_feature,
            start_date=dt.date(2015, 6, 1), end_date=dt.date(2015, 6, 2),
            consumed_units=consumed_during_second_trial_part)

        # # TEST ##
        call_command('generate_docs', billing_date=prev_billing_date, stdout=self.output)

        assert Proforma.objects.all().count() == 1
        assert Invoice.objects.all().count() == 0

        proforma = Proforma.objects.all()[0]
        assert proforma.total == Decimal('0.0000')

        # Expect 6 entries:
        # - plan trial may (+-)
        # - mfs trial may (+-)
        # - plan trial june (+-)
        assert proforma.proforma_entries.count() == 6
        assert all([entry.prorated
                    for entry in proforma.proforma_entries.all()])
        assert all([entry.total != Decimal('0.0000')
                    for entry in proforma.proforma_entries.all()])
        call_command('generate_docs', billing_date=curr_billing_date, stdout=self.output)

        assert Proforma.objects.all().count() == 2
        assert Invoice.objects.all().count() == 0

        proforma = Proforma.objects.all()[1]
        # Expect 2 entries:
        # - mfs trial extra june (+)
        # - remaining plan for june (+)
        assert proforma.proforma_entries.count() == 2
        first_entry = proforma.proforma_entries.first()
        assert first_entry.start_date == dt.date(2015, 6, 1)
        assert first_entry.end_date == subscription.trial_end

        second_entry = proforma.proforma_entries.last()
        assert second_entry.start_date == subscription.trial_end + ONE_DAY
        assert second_entry.end_date == dt.date(2015, 6, 30)

        prorated_plan_value = Decimal(28 / 30.0).quantize(Decimal('0.0000')) * plan.amount
        extra_mfs_during_trial = consumed_during_second_trial_part * mf_price
        assert proforma.total == prorated_plan_value + extra_mfs_during_trial

    def test_2nd_sub_billing_after_trial_with_some_consumed_units_overflow(self):
        """
        The subscription:
            * start_date=2015-05-20
            * trial_end=2015-06-03
            * first billing_date=2015-06-01
            * second billing_date=2015-06-04 (right after the trial_end)
        During 2015-05-20->2015-06-03 only a part of the included units have
        been consumed => a part remain for the 2015-06-01->2015-06-03
        """

        # # SETUP ##
        prev_billing_date = generate_docs_date('2015-06-01')
        curr_billing_date = generate_docs_date('2015-06-03')  # First day after trial_end

        customer = CustomerFactory.create(sales_tax_percent=Decimal('0.00'))

        included_during_trial = Decimal('12.00')
        mf_price = Decimal('2.5')
        metered_feature = MeteredFeatureFactory(
            included_units_during_trial=included_during_trial,
            price_per_unit=mf_price)
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  amount=Decimal('200.00'), trial_period_days=14,
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 5, 20)

        # Create the prorated subscription
        subscription = SubscriptionFactory.create(
            plan=plan, start_date=start_date, customer=customer)
        subscription.activate()
        subscription.save()
        consumed_during_first_trial_part = Decimal('10.00')
        consumed_during_second_trial_part = Decimal('12.00')
        MeteredFeatureUnitsLogFactory.create(
            subscription=subscription, metered_feature=metered_feature,
            start_date=dt.date(2015, 5, 20), end_date=dt.date(2015, 5, 31),
            consumed_units=consumed_during_first_trial_part
        )
        MeteredFeatureUnitsLogFactory.create(
            subscription=subscription, metered_feature=metered_feature,
            start_date=dt.date(2015, 6, 1), end_date=dt.date(2015, 6, 2),
            consumed_units=consumed_during_second_trial_part
        )

        # # TEST ##
        call_command('generate_docs', billing_date=prev_billing_date, stdout=self.output)

        assert Proforma.objects.all().count() == 1
        assert Invoice.objects.all().count() == 0

        proforma = Proforma.objects.first()
        # Expect 2 entries:
        # - plan trial may (+-)
        # - mfs trial may (+-)
        # - plan trial june (+-)
        assert all([entry.prorated for entry in proforma.proforma_entries.all()])
        assert proforma.proforma_entries.count() == 6
        assert proforma.total == Decimal('0.0000')

        call_command('generate_docs', billing_date=curr_billing_date, stdout=self.output)

        assert Proforma.objects.all().count() == 2
        assert Invoice.objects.all().count() == 0

        proforma = Proforma.objects.all()[1]
        # Expect 4 entries:
        # - mfs trial june (+-)
        # - mfs trial extra june (+)
        # - prorated subscription for the remaining period
        assert proforma.proforma_entries.count() == 4
        assert all([entry.prorated
                    for entry in proforma.proforma_entries.all()])
        assert all([entry.total != Decimal('0.0000')
                    for entry in proforma.proforma_entries.all()])
        prorated_plan_value = Decimal(28 / 30.0).quantize(Decimal('0.0000')) * plan.amount
        extra_mfs_during_trial = 10 * mf_price
        assert proforma.total == prorated_plan_value + extra_mfs_during_trial

    def test_2nd_sub_after_prorated_month_without_trial_without_consumed_units(self):
        """
        The subscription:
            * start_date=2015-05-20, no trial
            * first billing_date=2015-05-20 (right after activating
            the subscription)
            * second billing_date=2015-06-01
        It has 0 consumed units during 2015-05-20 -> 2015-06-01.
        """

        # # SETUP ##
        prev_billing_date = generate_docs_date('2015-05-20')
        curr_billing_date = generate_docs_date('2015-06-01')

        customer = CustomerFactory.create(sales_tax_percent=Decimal('0.00'))

        metered_feature = MeteredFeatureFactory()
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  amount=Decimal('200.00'),
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 5, 20)

        # Create the prorated subscription
        subscription = SubscriptionFactory.create(
            plan=plan, start_date=start_date, customer=customer)
        subscription.activate()
        subscription.save()

        # # TEST ##
        call_command('generate_docs', date=prev_billing_date,
                     subscription=subscription.id, stdout=self.output)

        assert Proforma.objects.all().count() == 1
        assert Invoice.objects.all().count() == 0

        percent = Decimal(12 / 31.0).quantize(Decimal('0.0000'))
        assert Proforma.objects.all()[0].total == percent * plan.amount

        call_command('generate_docs', date=curr_billing_date,
                     subscription=subscription.id, stdout=self.output)

        assert Proforma.objects.all().count() == 2
        assert Invoice.objects.all().count() == 0

        proforma = Proforma.objects.all()[1]
        # Expect 2 entries: the subscription for the next month
        # One entry for the 0 consumed mfs
        assert proforma.proforma_entries.count() == 2
        assert proforma.total == plan.amount

    def test_full_month_with_consumed_units(self):
        billing_date = generate_docs_date('2015-07-01')

        customer = CustomerFactory.create(sales_tax_percent=Decimal('0.00'))

        mf_price = Decimal('2.5')
        included_units = Decimal('20.00')
        metered_feature = MeteredFeatureFactory(
            price_per_unit=mf_price, included_units=Decimal('20.00'))
        provider = ProviderFactory.create()
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  amount=Decimal('200.00'),
                                  provider=provider,
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 2, 14)

        subscription = SubscriptionFactory.create(
            plan=plan, start_date=start_date, customer=customer)
        subscription.activate()
        subscription.save()

        BillingLog.objects.create(subscription=subscription,
                                  billing_date=dt.date(2015, 6, 1),
                                  metered_features_billed_up_to=dt.date(2015, 5, 31),
                                  plan_billed_up_to=dt.date(2015, 6, 30))

        consumed_units = Decimal('40.0000')
        MeteredFeatureUnitsLogFactory.create(
            subscription=subscription, metered_feature=metered_feature,
            start_date=dt.date(2015, 6, 1), end_date=dt.date(2015, 6, 30),
            consumed_units=consumed_units)

        call_command('generate_docs', date=billing_date, stdout=self.output)

        assert Proforma.objects.all().count() == 1
        assert Invoice.objects.all().count() == 0

        proforma = Proforma.objects.all()[0]
        assert proforma.proforma_entries.all().count() == 2
        assert all([not entry.prorated
                    for entry in proforma.proforma_entries.all()])
        consumed_mfs_value = (consumed_units - included_units) * mf_price
        assert proforma.total == plan.amount + consumed_mfs_value

    def test_full_month_without_consumed_units(self):
        billing_date = generate_docs_date('2015-07-01')

        customer = CustomerFactory.create(sales_tax_percent=Decimal('0.00'))

        metered_feature = MeteredFeatureFactory()
        provider = ProviderFactory.create()
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  amount=Decimal('200.00'), provider=provider,
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 2, 14)

        subscription = SubscriptionFactory.create(
            plan=plan, start_date=start_date, customer=customer)
        subscription.activate()
        subscription.save()

        BillingLog.objects.create(subscription=subscription,
                                  billing_date=dt.date(2015, 6, 1),
                                  metered_features_billed_up_to=dt.date(2015, 5, 31),
                                  plan_billed_up_to=dt.date(2015, 6, 30))

        call_command('generate_docs', date=billing_date, stdout=self.output)

        assert Proforma.objects.all().count() == 1
        assert Invoice.objects.all().count() == 0

        proforma = Proforma.objects.all()[0]
        assert proforma.proforma_entries.all().count() == 2
        assert proforma.total == plan.amount

    def test_gen_proforma_to_issued_state_for_one_provider(self):
        billing_date = generate_docs_date('2015-03-02')

        customer = CustomerFactory.create(
            consolidated_billing=False, sales_tax_percent=Decimal('0.00'))
        metered_feature = MeteredFeatureFactory(included_units=Decimal('20.00'))
        provider = ProviderFactory.create(default_document_state='issued')
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  amount=Decimal('200.00'), provider=provider,
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 2, 14)

        # Create the prorated subscription
        subscription = SubscriptionFactory.create(
            plan=plan, start_date=start_date, customer=customer)
        subscription.activate()
        subscription.save()

        mocked_should_be_billed = MagicMock(return_value=True)
        with patch.multiple('silver.models.Subscription',
                            should_be_billed=mocked_should_be_billed):
            call_command('generate_docs', billing_date=billing_date,
                         stdout=self.output)

            assert Proforma.objects.all().count() == 1
            assert Invoice.objects.all().count() == 0

            assert Proforma.objects.all().first().state == Proforma.STATES.ISSUED

    def test_gen_mixed_states_for_multiple_providers(self):
        billing_date = generate_docs_date('2015-03-02')

        customer = CustomerFactory.create(
            consolidated_billing=False, sales_tax_percent=Decimal('0.00'))
        metered_feature = MeteredFeatureFactory(
            included_units=Decimal('20.00'))
        provider_draft = ProviderFactory.create(
            default_document_state='draft')
        provider_issued = ProviderFactory.create(
            default_document_state='issued')
        plan_price = Decimal('200.00')
        plan1 = PlanFactory.create(interval='month', interval_count=1,
                                   generate_after=120, enabled=True,
                                   amount=plan_price, provider=provider_draft,
                                   metered_features=[metered_feature])
        plan2 = PlanFactory.create(interval='month', interval_count=1,
                                   generate_after=120, enabled=True,
                                   amount=plan_price, provider=provider_issued,
                                   metered_features=[metered_feature])
        start_date = dt.date(2015, 2, 14)

        # Create the prorated subscription
        subscription1 = SubscriptionFactory.create(
            plan=plan1, start_date=start_date, customer=customer)
        subscription1.activate()
        subscription1.save()

        subscription2 = SubscriptionFactory.create(
            plan=plan2, start_date=start_date, customer=customer)
        subscription2.activate()
        subscription2.save()

        mocked_last_billing_date = PropertyMock(
            return_value=dt.date(2015, 2, 14))
        mocked_is_billed_first_time = PropertyMock(return_value=False)
        mocked_get_consumed_units_during_trial = MagicMock(return_value=(0, 0))
        with patch.multiple(
            'silver.models.Subscription',
            last_billing_date=mocked_last_billing_date,
            is_billed_first_time=mocked_is_billed_first_time,
            _get_extra_consumed_units_during_trial=mocked_get_consumed_units_during_trial
        ):

            call_command('generate_docs', billing_date=billing_date,
                         stdout=self.output)

            assert Proforma.objects.all().count() == 2
            assert Invoice.objects.all().count() == 0

            assert Proforma.objects.all()[0].state == Proforma.STATES.ISSUED
            assert Proforma.objects.all()[1].state == Proforma.STATES.DRAFT

    def test_cancel_sub_without_trial_at_end_of_billing_cycle(self):
        """
        It has consumed mfs between start_date -> end_of_month
        """

        # # SETUP ##
        prev_billing_date = generate_docs_date('2015-05-20')
        random_billing_date = generate_docs_date('2015-05-27')
        curr_billing_date = generate_docs_date('2015-06-01')

        customer = CustomerFactory.create(sales_tax_percent=Decimal('0.00'))

        metered_feature = MeteredFeatureFactory(
            included_units=Decimal('0.0000'),
            price_per_unit=Decimal('2.5'))
        plan = PlanFactory.create(interval=Plan.INTERVALS.MONTH,
                                  interval_count=1, generate_after=120,
                                  enabled=True, amount=Decimal('200.00'),
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 5, 20)
        end_of_month = dt.date(2015, 5, 31)

        # Create the prorated subscription
        subscription = SubscriptionFactory.create(
            plan=plan, start_date=start_date, customer=customer
        )
        subscription.activate()
        subscription.save()

        # # TEST ##

        # RUN 1
        call_command('generate_docs', billing_date=prev_billing_date, stdout=self.output)

        assert Proforma.objects.all().count() == 1
        assert Invoice.objects.all().count() == 0

        # It should add the prorated value of the plan for the rest of the
        # month
        prorated_days = (end_of_month - start_date).days + 1
        prorated_plan_value = Decimal(prorated_days / 31.0).quantize(
            Decimal('0.0000')) * plan.amount
        assert Proforma.objects.all()[0].total == prorated_plan_value

        # RUN 2
        call_command('generate_docs', billing_date=random_billing_date, stdout=self.output)

        # It should be ignored
        assert Proforma.objects.all().count() == 1
        assert Invoice.objects.all().count() == 0

        # Move it to `canceled` state
        subscription.cancel(when=Subscription.CANCEL_OPTIONS.END_OF_BILLING_CYCLE)
        subscription.cancel_date = dt.date(2015, 5, 31)
        subscription.save()

        # Consume some mfs
        consumed_mfs = Decimal('5.00')
        MeteredFeatureUnitsLogFactory.create(
            subscription=subscription, metered_feature=metered_feature,
            start_date=start_date, end_date=end_of_month,
            consumed_units=consumed_mfs)

        # RUN 3
        call_command('generate_docs', billing_date=curr_billing_date, stdout=self.output)

        assert Proforma.objects.all().count() == 2
        assert Invoice.objects.all().count() == 0

        proforma = Proforma.objects.all()[1]
        assert proforma.proforma_entries.count() == 1
        assert all([entry.prorated
                    for entry in proforma.proforma_entries.all()])
        assert all([entry.total != Decimal('0.0000')
                    for entry in proforma.proforma_entries.all()])
        consumed_mfs_value = consumed_mfs * metered_feature.price_per_unit
        assert proforma.total == consumed_mfs_value

    ###########################################################################
    # Canceled
    ###########################################################################
    def test_canceled_subscription_with_trial_and_consumed_metered_features_draft(self):
        """
        Subscription with consumed mfs both during trial and afterwards,
        canceled in the same month it started.

        start_date = 2015-02-01
        trial_end  = 2015-02-08 -- has consumed units during trial period
        end_date   = 2015-02-28 -- has consumed units between trial and end_date
        """

        billing_date = generate_docs_date('2015-03-01')

        metered_feature = MeteredFeatureFactory(included_units=Decimal('0.00'))
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  trial_period_days=7, amount=Decimal('200.00'),
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 2, 1)
        trial_end = start_date + dt.timedelta(days=plan.trial_period_days)

        subscription = SubscriptionFactory.create(
            plan=plan, start_date=start_date, trial_end=trial_end)
        subscription.activate()
        subscription.save()

        mf_units_log_during_trial = MeteredFeatureUnitsLogFactory(
            subscription=subscription, metered_feature=metered_feature,
            start_date=start_date, end_date=trial_end)

        mf_units_log_after_trial = MeteredFeatureUnitsLogFactory(
            subscription=subscription, metered_feature=metered_feature,
            start_date=trial_end + dt.timedelta(days=1),
            # canceled 4 days before the end of the month
            end_date=dt.datetime(2015, 2, 28))

        subscription.cancel(when=Subscription.CANCEL_OPTIONS.END_OF_BILLING_CYCLE)
        subscription.cancel_date = dt.date(2015, 2, 28)
        subscription.save()

        call_command('generate_docs', billing_date=billing_date, stdout=self.output)

        # Expect one Proforma
        assert Proforma.objects.all().count() == 1
        assert Invoice.objects.all().count() == 0

        # In draft state
        assert Proforma.objects.all()[0].state == Proforma.STATES.DRAFT
        # Expect 6 entries:
        # Plan Trial (+-), Plan Trial Metered Feature (+-),
        # Plan After Trial (+),  Metered Features After Trial (+)
        document_entries = DocumentEntry.objects.all()
        assert len(document_entries) == 6

        doc = document_entries[0]  # Plan trial (+)
        assert doc.unit_price == Decimal('57.14')

        doc = document_entries[1]  # Plan trial (-)
        assert doc.unit_price == Decimal('-57.14')

        doc = document_entries[2]  # Consumed mf (+)
        assert doc.unit_price == metered_feature.price_per_unit
        assert doc.quantity == mf_units_log_during_trial.consumed_units

        doc = document_entries[3]  # Consumed mf (-)
        assert doc.unit_price == - metered_feature.price_per_unit
        assert doc.quantity == mf_units_log_during_trial.consumed_units

        doc = document_entries[4]  # Plan after trial end
        assert doc.unit_price == Decimal(20.0 / 28).quantize(Decimal('0.0000')) * plan.amount

        doc = document_entries[5]  # Consumed mf after trial
        assert doc.unit_price == metered_feature.price_per_unit
        assert doc.quantity == mf_units_log_after_trial.consumed_units

    def test_canceled_subscription_with_metered_features_to_draft(self):
        """
        start_date        = 2015-01-01
        trial_end         = 2015-01-08
        last_billing_date = 2015-02-01
        """
        billing_date = generate_docs_date('2015-03-01')

        metered_feature = MeteredFeatureFactory(included_units=Decimal('0.00'))
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  trial_period_days=7, amount=Decimal('200.00'),
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 1, 1)

        subscription = SubscriptionFactory.create(plan=plan, start_date=start_date)
        subscription.activate()
        subscription.save()

        mf_units_log = MeteredFeatureUnitsLogFactory(
            subscription=subscription, metered_feature=metered_feature,
            start_date=dt.datetime(2015, 2, 1),
            end_date=dt.datetime(2015, 2, 28)
        )

        subscription.cancel(when=Subscription.CANCEL_OPTIONS.END_OF_BILLING_CYCLE)
        subscription.cancel_date = dt.date(2015, 2, 28)
        subscription.save()

        BillingLog.objects.create(subscription=subscription,
                                  billing_date=dt.date(2015, 2, 1),
                                  plan_billed_up_to=dt.date(2015, 2, 28),
                                  metered_features_billed_up_to=dt.date(2015, 1, 31))

        call_command('generate_docs', billing_date=billing_date, stdout=self.output)

        # Expect one Proforma
        assert Proforma.objects.all().count() == 1
        assert Invoice.objects.all().count() == 0

        # Expect 1 entry:
        # Extra Metered Features (+)
        assert DocumentEntry.objects.all().count() == 1

        doc = DocumentEntry.objects.all()[0]
        assert doc.unit_price == metered_feature.price_per_unit
        assert doc.quantity == mf_units_log.consumed_units

    def test_canceled_subscription_with_trial_and_trial_underflow(self):
        """
        A subscription that was canceled in the same month as it started,
        the customer consuming less metered features than
        included_units_during_trial.
        """

        billing_date = generate_docs_date('2015-03-01')

        metered_feature = MeteredFeatureFactory(
            included_units=Decimal('0.00'),
            included_units_during_trial=Decimal('5.00'))
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  trial_period_days=7, amount=Decimal('200.00'),
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 2, 1)

        subscription = SubscriptionFactory.create(plan=plan, start_date=start_date)
        subscription.activate()
        subscription.save()

        trial_quantity = Decimal('3.00')
        MeteredFeatureUnitsLogFactory(
            subscription=subscription, metered_feature=metered_feature,
            start_date=start_date, end_date=subscription.trial_end,
            consumed_units=trial_quantity)

        mf_units_log_after_trial = MeteredFeatureUnitsLogFactory(
            subscription=subscription, metered_feature=metered_feature,
            start_date=subscription.trial_end + dt.timedelta(days=1),
            end_date=dt.datetime(2015, 2, 28)
        )

        subscription.cancel(when=Subscription.CANCEL_OPTIONS.END_OF_BILLING_CYCLE)
        subscription.cancel_date = dt.date(2015, 2, 28)
        subscription.save()

        call_command('generate_docs', billing_date=billing_date, stdout=self.output)

        # Expect one Proforma
        assert Proforma.objects.all().count() == 1
        assert Invoice.objects.all().count() == 0

        # In draft state
        assert Proforma.objects.all()[0].state == Proforma.STATES.DRAFT

        document_entries = DocumentEntry.objects.all()
        # Expect 6 entries:
        # Plan Trial (+-), Plan Trial Metered Feature (+-),
        # Plan After Trial (+),  Metered Features After Trial (+)
        assert len(document_entries) == 6

        doc = document_entries[0]  # Plan trial (+)
        assert doc.unit_price == Decimal(7.0 / 28).quantize(Decimal('0.0000')) * plan.amount

        doc = document_entries[1]  # Plan trial (-)
        assert doc.unit_price == Decimal(-7.0 / 28).quantize(Decimal('0.0000')) * plan.amount

        doc = document_entries[2]  # Consumed mf (+)
        assert doc.unit_price == metered_feature.price_per_unit
        assert doc.quantity == trial_quantity

        doc = document_entries[3]  # Consumed mf (-)
        assert doc.unit_price == - metered_feature.price_per_unit
        assert doc.quantity == trial_quantity

        doc = document_entries[4]  # Plan after trial end
        assert doc.unit_price == Decimal(21.0 / 28).quantize(Decimal('0.0000')) * plan.amount

        doc = document_entries[5]  # Consumed mf after trial
        assert doc.unit_price == metered_feature.price_per_unit
        assert doc.quantity == mf_units_log_after_trial.consumed_units

    def test_canceled_subscription_with_trial_and_trial_overflow(self):
        billing_date = generate_docs_date('2015-03-01')

        units_included_during_trial = Decimal('5.00')
        metered_feature = MeteredFeatureFactory(
            included_units=Decimal('0.00'),
            included_units_during_trial=units_included_during_trial)
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  trial_period_days=7, amount=Decimal('200.00'),
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 2, 1)

        subscription = SubscriptionFactory.create(plan=plan, start_date=start_date)
        subscription.activate()
        subscription.save()

        units_consumed_during_trial = Decimal('7.00')
        MeteredFeatureUnitsLogFactory(
            subscription=subscription, metered_feature=metered_feature,
            start_date=start_date, end_date=subscription.trial_end,
            consumed_units=units_consumed_during_trial)

        mf_units_log_after_trial = MeteredFeatureUnitsLogFactory(
            subscription=subscription, metered_feature=metered_feature,
            start_date=subscription.trial_end + dt.timedelta(days=1),
            end_date=dt.datetime(2015, 2, 28)
        )

        subscription.cancel(
            when=Subscription.CANCEL_OPTIONS.END_OF_BILLING_CYCLE
        )
        subscription.cancel_date = dt.date(2015, 2, 28)
        subscription.save()

        call_command('generate_docs', billing_date=billing_date,
                     stdout=self.output)

        # Expect one Proforma
        assert Proforma.objects.all().count() == 1
        assert Invoice.objects.all().count() == 0

        # In draft state
        assert Proforma.objects.all()[0].state == Proforma.STATES.DRAFT

        document_entries = DocumentEntry.objects.all()
        # Expect 7 entries:
        # Plan Trial (+-), Plan Trial Metered Feature (+-),
        # Extra consumed mf
        # Plan After Trial (+),  Metered Features After Trial (+)
        assert len(document_entries) == 7

        doc = document_entries[0]  # Plan trial (+)
        assert doc.unit_price == Decimal(7.0 / 28).quantize(Decimal('0.0000')) * plan.amount

        doc = document_entries[1]  # Plan trial (-)
        assert doc.unit_price == Decimal(-7.0 / 28).quantize(Decimal('0.0000')) * plan.amount

        doc = document_entries[2]  # Consumed mf (+)
        assert doc.unit_price == metered_feature.price_per_unit
        assert doc.quantity == units_included_during_trial

        doc = document_entries[3]  # Consumed mf (-)
        assert doc.unit_price == - metered_feature.price_per_unit
        assert doc.quantity == units_included_during_trial

        doc = document_entries[4]  # Consumed mf (-)
        assert doc.unit_price == metered_feature.price_per_unit
        assert doc.quantity == units_consumed_during_trial - units_included_during_trial

        doc = document_entries[5]  # Plan after trial end
        assert doc.unit_price == Decimal(21.0 / 28).quantize(Decimal('0.0000')) * plan.amount

        doc = document_entries[6]  # Consumed mf after trial
        assert doc.unit_price == metered_feature.price_per_unit
        assert doc.quantity == mf_units_log_after_trial.consumed_units

    def test_gen_for_single_canceled_subscription_during_trial(self):
        plan = PlanFactory.create(interval=Plan.INTERVALS.MONTH,
                                  interval_count=1, generate_after=120,
                                  enabled=True, trial_period_days=7,
                                  amount=Decimal('200.00'))

        subscription = SubscriptionFactory.create(plan=plan, start_date=dt.date(2015, 1, 3))
        subscription.activate()
        subscription.cancel(when=Subscription.CANCEL_OPTIONS.NOW)
        subscription.cancel_date = dt.date(2015, 1, 6)
        subscription.save()

        call_command('generate_docs', date=generate_docs_date('2015-01-06'),
                     subscription=subscription.pk, stdout=self.output)

        assert Subscription.objects.filter(state='ended').count() == 0

        # the date after the cancel date
        call_command('generate_docs', date=generate_docs_date('2015-01-07'),
                     subscription=subscription.pk, stdout=self.output)

        assert Subscription.objects.filter(state='ended').count() == 1

        assert Proforma.objects.all().count() == 1
        assert Invoice.objects.all().count() == 0

        proforma = Proforma.objects.all()[0]

        assert proforma.proforma_entries.count() == 2
        for entry in proforma.proforma_entries.all():
            assert entry.prorated
            assert entry.start_date == subscription.start_date
            assert entry.end_date == subscription.cancel_date

        assert proforma.total == Decimal('0.0000')

    def test_gen_active_and_canceled_selection(self):
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  trial_period_days=7, amount=Decimal('200.00'))
        start_date = dt.date(2015, 1, 29)

        SubscriptionFactory.create_batch(size=5, plan=plan, start_date=start_date)

        for subscription in Subscription.objects.all():
            subscription.activate()
            subscription.save()

        cancel_date = dt.date(2015, 1, 29)

        for subscription in Subscription.objects.all()[2:5]:
            subscription.cancel(when=Subscription.CANCEL_OPTIONS.NOW)
            subscription.cancel_date = cancel_date
            subscription.save()

        call_command('generate_docs', billing_date=cancel_date, stdout=self.output)
        # Expect 2 Proformas from the active subs
        assert Proforma.objects.all().count() == 2
        assert Subscription.objects.filter(state='ended').count() == 0

        call_command('generate_docs', billing_date=cancel_date + ONE_DAY, stdout=self.output)

        # Expect 5 Proformas (2 active Subs, 3 canceled)
        assert Proforma.objects.all().count() == 5
        assert Invoice.objects.all().count() == 0

        assert Subscription.objects.filter(state='ended').count() == 3

    def test_subscription_with_separate_cycles_during_trial(self):
        separate_cycles_during_trial = True
        prebill_plan = False
        generate_documents_on_trial_end = False

        metered_feature = MeteredFeatureFactory(
            included_units_during_trial=Decimal('5.00'),
            price_per_unit=Decimal('1.00')
        )
        plan = PlanFactory.create(interval=Plan.INTERVALS.MONTH,
                                  interval_count=1, generate_after=120,
                                  enabled=True, trial_period_days=15,
                                  amount=Decimal('200.00'),
                                  separate_cycles_during_trial=separate_cycles_during_trial,
                                  generate_documents_on_trial_end=generate_documents_on_trial_end,
                                  prebill_plan=prebill_plan,
                                  metered_features=[metered_feature])

        subscription = SubscriptionFactory.create(plan=plan, start_date=dt.date(2015, 1, 25))
        subscription.activate()
        subscription.save()
        subscription.customer.sales_tax_percent = None
        subscription.customer.save()

        mf_log = MeteredFeatureUnitsLogFactory.create(
            subscription=subscription, metered_feature=metered_feature,
            start_date=subscription.start_date, end_date=dt.date(2015, 1, 31),
            consumed_units=Decimal('5.00')
        )

        call_command('generate_docs', date=generate_docs_date('2015-01-25'), stdout=self.output)

        assert Proforma.objects.all().count() == 0

        call_command('generate_docs', date=generate_docs_date('2015-02-01'), stdout=self.output)

        assert Proforma.objects.all().count() == 1

        proforma = Proforma.objects.all()[0]
        assert proforma.total == Decimal('0.00')
        assert proforma.proforma_entries.count() == 4  # plan trial and consumed mfs
        for entry in proforma.proforma_entries.all():
            if entry.product_code == plan.product_code:
                unit_price = Decimal(7 / 31.0).quantize(Decimal('0.0000')) * plan.amount
                assert entry.quantity == 1
            else:
                assert entry.quantity == mf_log.consumed_units
                unit_price = metered_feature.price_per_unit

            if entry.unit_price < 0:  # discount
                unit_price *= -1

            assert entry.unit_price == unit_price
            assert entry.prorated
            assert entry.start_date == subscription.start_date
            assert entry.end_date == dt.date(2015, 1, 31)

        call_command('generate_docs', date=generate_docs_date('2015-03-01'),
                     subscription=subscription.pk, stdout=self.output)

        assert Proforma.objects.all().count() == 2
        proforma = Proforma.objects.all()[1]

        billed_plan_amount = Decimal(20 / 28.0).quantize(Decimal('0.0000')) * plan.amount
        assert proforma.total == billed_plan_amount

        assert proforma.proforma_entries.count() == 4  # plan trial (+-), plan (+) and mfs (0)
        for entry in proforma.proforma_entries.all():
            if entry.product_code == plan.product_code:
                assert entry.quantity == 1
                if entry.start_date == dt.date(2015, 2, 1):  # trial
                    unit_price = plan.amount - billed_plan_amount
                    assert entry.end_date == dt.date(2015, 2, 8)
                else:
                    assert entry.start_date == dt.date(2015, 2, 9)
                    assert entry.end_date == dt.date(2015, 2, 28)
                    unit_price = billed_plan_amount
            else:
                assert entry.quantity == Decimal('0.00')
                assert entry.start_date == subscription.trial_end + ONE_DAY
                assert entry.end_date == dt.date(2015, 2, 28)
                unit_price = entry.unit_price

            if entry.unit_price < 0:  # discount
                unit_price *= -1

            assert entry.unit_price == unit_price
            assert entry.prorated

        call_command('generate_docs', date=generate_docs_date('2015-02-10'),
                     subscription=subscription.pk, stdout=self.output)
        assert Proforma.objects.all().count() == 2

    def test_subscription_with_documents_generation_on_trial_end(self):
        separate_cycles_during_trial = False
        generate_documents_on_trial_end = True

        metered_feature = MeteredFeatureFactory(
            included_units_during_trial=Decimal('5.00'),
            price_per_unit=Decimal('1.00')
        )
        plan = PlanFactory.create(interval=Plan.INTERVALS.MONTH,
                                  interval_count=1, generate_after=120,
                                  enabled=True, trial_period_days=15,
                                  amount=Decimal('200.00'),
                                  separate_cycles_during_trial=separate_cycles_during_trial,
                                  generate_documents_on_trial_end=generate_documents_on_trial_end,
                                  metered_features=[metered_feature])

        subscription = SubscriptionFactory.create(plan=plan, start_date=dt.date(2015, 1, 25))
        subscription.activate()
        subscription.save()
        subscription.customer.sales_tax_percent = None
        subscription.customer.save()

        mf_log = MeteredFeatureUnitsLogFactory.create(
            subscription=subscription, metered_feature=metered_feature,
            start_date=subscription.start_date, end_date=dt.date(2015, 1, 31),
            consumed_units=Decimal('5.00')
        )

        call_command('generate_docs', date=generate_docs_date('2015-01-25'), stdout=self.output)

        assert Proforma.objects.all().count() == 1

        proforma = Proforma.objects.all()[0]
        assert proforma.total == Decimal('0.00')
        assert proforma.proforma_entries.count() == 4  # plan trial (+-) split by months (*2)
        for entry in proforma.proforma_entries.all():
            if entry.start_date == subscription.start_date:
                assert entry.end_date == dt.date(2015, 1, 31)
                unit_price = Decimal(7 / 31.0).quantize(Decimal('0.0000')) * plan.amount
            else:
                unit_price = Decimal(8 / 28.0).quantize(Decimal('0.0000')) * plan.amount
                assert entry.start_date == dt.date(2015, 2, 1)
                assert entry.end_date == subscription.trial_end

            if entry.unit_price < 0:  # discount
                unit_price *= -1

            assert entry.quantity == 1
            assert entry.unit_price == unit_price
            assert entry.prorated

        call_command('generate_docs', date=generate_docs_date('2015-02-01'), stdout=self.output)

        assert Proforma.objects.all().count() == 1

        call_command('generate_docs', date=generate_docs_date('2015-02-09'), stdout=self.output)
        proforma = Proforma.objects.all()[1]

        plan_amount = Decimal(20 / 28.0).quantize(Decimal('0.0000')) * plan.amount
        assert proforma.proforma_entries.count() == 3  # mfs during trial (+-) and remaining plan

        for entry in proforma.proforma_entries.all():
            if entry.product_code == plan.product_code:
                assert entry.quantity == 1
                unit_price = plan_amount
            else:
                assert entry.quantity == mf_log.consumed_units
                unit_price = metered_feature.price_per_unit

            if entry.unit_price < 0:  # discount
                unit_price *= -1

            assert entry.unit_price == unit_price
            assert entry.prorated
        assert proforma.total == plan_amount

        call_command('generate_docs', date=generate_docs_date('2015-02-10'), stdout=self.output)
        assert Proforma.objects.all().count() == 2

    def test_subscription_with_documents_generation_during_and_after_trial(self):
        separate_cycles_during_trial = True
        generate_documents_on_trial_end = True

        metered_feature = MeteredFeatureFactory(
            included_units_during_trial=Decimal('5.00'),
            price_per_unit=Decimal('1.00')
        )
        plan = PlanFactory.create(interval=Plan.INTERVALS.MONTH,
                                  interval_count=1, generate_after=120,
                                  enabled=True, trial_period_days=15,
                                  amount=Decimal('200.00'),
                                  separate_cycles_during_trial=separate_cycles_during_trial,
                                  generate_documents_on_trial_end=generate_documents_on_trial_end,
                                  metered_features=[metered_feature])

        subscription = SubscriptionFactory.create(plan=plan, start_date=dt.date(2015, 1, 25))
        subscription.activate()
        subscription.save()
        subscription.customer.sales_tax_percent = None
        subscription.customer.save()

        mf_log = MeteredFeatureUnitsLogFactory.create(
            subscription=subscription, metered_feature=metered_feature,
            start_date=subscription.start_date, end_date=dt.date(2015, 1, 31),
            consumed_units=Decimal('5.00')
        )

        call_command('generate_docs', date=generate_docs_date('2015-01-25'), stdout=self.output)

        assert Proforma.objects.all().count() == 1

        proforma = Proforma.objects.all()[0]
        assert proforma.total == Decimal('0.00')
        assert proforma.proforma_entries.count() == 2  # plan trial for january (+-)
        for entry in proforma.proforma_entries.all():
            assert entry.start_date == subscription.start_date
            assert entry.end_date == dt.date(2015, 1, 31)
            unit_price = Decimal(7 / 31.0).quantize(Decimal('0.0000')) * plan.amount

            if entry.unit_price < 0:
                unit_price *= -1

            assert entry.quantity == 1
            assert entry.unit_price == unit_price
            assert entry.prorated

        call_command('generate_docs', date=generate_docs_date('2015-02-01'), stdout=self.output)

        assert Proforma.objects.all().count() == 2

        proforma = Proforma.objects.all()[1]
        assert proforma.total == Decimal('0.00')

        # mfs for january (+-)
        # plan trial for february (+-)
        assert proforma.proforma_entries.count() == 4
        for entry in proforma.proforma_entries.all():
            if entry.product_code == plan.product_code:
                assert entry.quantity == 1
                unit_price = Decimal(8 / 28.0).quantize(Decimal('0.0000')) * plan.amount
            else:
                assert entry.quantity == mf_log.consumed_units
                unit_price = metered_feature.price_per_unit

            if entry.unit_price < 0:  # discount
                unit_price *= -1

            assert entry.unit_price == unit_price
            assert entry.prorated

        call_command('generate_docs', date=generate_docs_date('2015-02-09'), stdout=self.output)
        assert Proforma.objects.all().count() == 3

        proforma = Proforma.objects.all()[2]
        plan_amount = Decimal(20 / 28.0).quantize(Decimal('0.0000')) * plan.amount
        assert proforma.total == plan_amount

        assert proforma.proforma_entries.count() == 1  # remaining plan (+)

        for entry in proforma.proforma_entries.all():
            if entry.product_code == plan.product_code:
                assert entry.quantity == 1
                unit_price = plan_amount
            else:
                assert entry.quantity == mf_log.consumed_units
                unit_price = metered_feature.price_per_unit

            if entry.unit_price < 0:  # discount
                unit_price *= -1

            assert entry.unit_price == unit_price
            assert entry.prorated

        call_command('generate_docs', date=generate_docs_date('2015-02-10'), stdout=self.output)
        assert Proforma.objects.all().count() == 3

    def test_subscription_cycle_billing_duration(self):
        plan = PlanFactory.create(interval=Plan.INTERVALS.MONTH,
                                  interval_count=1, generate_after=120,
                                  enabled=True, trial_period_days=15,
                                  amount=Decimal('200.00'),
                                  cycle_billing_duration=dt.timedelta(days=5))

        subscription = SubscriptionFactory.create(plan=plan, start_date=dt.date(2015, 1, 25))
        subscription.activate()
        subscription.save()
        subscription.customer.sales_tax_percent = None
        subscription.customer.save()

        call_command('generate_docs', date=generate_docs_date('2015-01-25'), stdout=self.output)

        assert Proforma.objects.all().count() == 0

        billing_date = dt.date(2015, 2, 1)
        call_command('generate_docs', date=billing_date, stdout=self.output)

        assert Proforma.objects.all().count() == 1

        billing_log = BillingLog.objects.filter(subscription=subscription).last()

        assert billing_log.billing_date == billing_date
