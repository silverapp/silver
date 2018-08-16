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

import datetime

from freezegun import freeze_time
from mock import patch, PropertyMock, MagicMock

from django.test import TestCase

from silver.models import Plan, Subscription, BillingLog
from silver.tests.factories import (SubscriptionFactory, MeteredFeatureFactory,
                                    PlanFactory)


class TestSubscription(TestCase):
    def test_subscription_mf_units_log_intervals_1(self):
        # Every month, 16 days of trial

        subscription = SubscriptionFactory.create()
        metered_feature = MeteredFeatureFactory.create()

        subscription.plan.metered_features.add(metered_feature)

        subscription.start_date = datetime.date(year=2015, month=2, day=17)
        subscription.activate()
        subscription.save()

        subscription.plan.interval = Plan.INTERVALS.MONTH
        subscription.plan.interval_count = 1
        subscription.plan.save()
        subscription.plan.separate_cycles_during_trial = True

        subscription.trial_end = (subscription.start_date +
                                  datetime.timedelta(days=15))

        start_date = subscription.start_date
        assert start_date == subscription.bucket_start_date(
            reference_date=datetime.date(year=2015, month=2, day=17))

        end_date = datetime.date(year=2015, month=2, day=28)
        assert end_date == subscription.bucket_end_date(
            reference_date=datetime.date(year=2015, month=2, day=23))

        start_date = datetime.date(year=2015, month=3, day=1)
        assert start_date == subscription.bucket_start_date(
            reference_date=datetime.date(year=2015, month=3, day=1))

        end_date = datetime.date(year=2015, month=3, day=4)
        assert end_date == subscription.bucket_end_date(
            reference_date=datetime.date(year=2015, month=3, day=1))

        start_date = datetime.date(year=2015, month=3, day=5)
        assert start_date == subscription.bucket_start_date(
            reference_date=datetime.date(year=2015, month=3, day=5))

        end_date = datetime.date(year=2015, month=3, day=31)
        assert end_date == subscription.bucket_end_date(
            reference_date=datetime.date(year=2015, month=3, day=22))

        start_date = datetime.date(year=2015, month=4, day=1)
        assert start_date == subscription.bucket_start_date(
            reference_date=datetime.date(year=2015, month=4, day=5))

        end_date = datetime.date(year=2015, month=4, day=30)
        assert end_date == subscription.bucket_end_date(
            reference_date=datetime.date(year=2015, month=4, day=22))

    def test_subscription_mf_units_log_intervals_2(self):
        # Every 2 months, 5 months of trial (2015-05-30)

        subscription = SubscriptionFactory.create()
        metered_feature = MeteredFeatureFactory.create()

        subscription.plan.metered_features.add(metered_feature)

        subscription.start_date = datetime.date(year=2015, month=2, day=17)
        subscription.activate()
        subscription.save()

        subscription.plan.interval = Plan.INTERVALS.MONTH
        subscription.plan.interval_count = 2
        subscription.plan.separate_cycles_during_trial = True
        subscription.plan.save()

        subscription.start_date = datetime.date(year=2014, month=12, day=31)
        subscription.trial_end = (subscription.start_date +
                                  datetime.timedelta(days=150))
        subscription.save()

        start_date = datetime.date(year=2014, month=12, day=31)
        assert start_date == subscription.bucket_start_date(
            reference_date=datetime.date(year=2014, month=12, day=31))

        end_date = datetime.date(year=2014, month=12, day=31)
        assert end_date == subscription.bucket_end_date(
            reference_date=datetime.date(year=2014, month=12, day=31))

        start_date = datetime.date(year=2015, month=1, day=1)
        assert start_date == subscription.bucket_start_date(
            reference_date=datetime.date(year=2015, month=1, day=1))

        end_date = datetime.date(year=2015, month=1, day=31)
        assert end_date == subscription.bucket_end_date(
            reference_date=datetime.date(year=2015, month=1, day=1))

        start_date = datetime.date(year=2015, month=3, day=1)
        assert start_date == subscription.bucket_start_date(
            reference_date=datetime.date(year=2015, month=3, day=23))

        end_date = datetime.date(year=2015, month=4, day=30)
        assert end_date == subscription.bucket_end_date(
            reference_date=datetime.date(year=2015, month=4, day=30))

        start_date = datetime.date(year=2015, month=5, day=1)
        assert start_date == subscription.bucket_start_date(
            reference_date=datetime.date(year=2015, month=5, day=23))

        end_date = datetime.date(year=2015, month=5, day=30)
        assert end_date == subscription.bucket_end_date(
            reference_date=datetime.date(year=2015, month=5, day=30))

        start_date = datetime.date(year=2015, month=6, day=1)
        assert start_date == subscription.bucket_start_date(
            reference_date=datetime.date(year=2015, month=6, day=1))

        end_date = datetime.date(year=2015, month=6, day=30)
        assert end_date == subscription.bucket_end_date(
            reference_date=datetime.date(year=2015, month=6, day=1))

    def test_subscription_mf_units_log_intervals_3(self):
        # Every 2 weeks, 8 days of trial

        subscription = SubscriptionFactory.create()
        metered_feature = MeteredFeatureFactory.create()

        subscription.plan.metered_features.add(metered_feature)

        subscription.start_date = datetime.date(year=2015, month=2, day=17)
        subscription.activate()
        subscription.save()

        subscription.plan.interval = Plan.INTERVALS.WEEK
        subscription.plan.interval_count = 2
        subscription.plan.separate_cycles_during_trial = True
        subscription.plan.save()

        subscription.start_date = datetime.date(year=2015, month=5, day=31)
        subscription.trial_end = (subscription.start_date +
                                  datetime.timedelta(days=7))
        subscription.save()

        start_date = datetime.date(year=2015, month=5, day=31)
        assert start_date == subscription.bucket_start_date(
            reference_date=datetime.date(year=2015, month=5, day=31))

        end_date = datetime.date(year=2015, month=5, day=31)
        assert end_date == subscription.bucket_end_date(
            reference_date=datetime.date(year=2015, month=5, day=31))

        start_date = datetime.date(year=2015, month=6, day=1)
        assert start_date == subscription.bucket_start_date(
            reference_date=datetime.date(year=2015, month=6, day=1))

        end_date = datetime.date(year=2015, month=6, day=7)
        assert end_date == subscription.bucket_end_date(
            reference_date=datetime.date(year=2015, month=6, day=1))

        start_date = datetime.date(year=2015, month=6, day=8)
        assert start_date == subscription.bucket_start_date(
            reference_date=datetime.date(year=2015, month=6, day=8))

        end_date = datetime.date(year=2015, month=6, day=14)
        assert end_date == subscription.bucket_end_date(
            reference_date=datetime.date(year=2015, month=6, day=8))

        start_date = datetime.date(year=2015, month=6, day=15)
        assert start_date == subscription.bucket_start_date(
            reference_date=datetime.date(year=2015, month=6, day=15))

        end_date = datetime.date(year=2015, month=6, day=28)
        assert end_date == subscription.bucket_end_date(
            reference_date=datetime.date(year=2015, month=6, day=28))

    def test_subscription_mf_units_log_intervals_4(self):
        # Every year, 3 months (90 days) of trial

        subscription = SubscriptionFactory.create()
        metered_feature = MeteredFeatureFactory.create()

        subscription.plan.metered_features.add(metered_feature)

        subscription.start_date = datetime.date(year=2015, month=2, day=17)
        subscription.activate()
        subscription.save()

        subscription.plan.interval = Plan.INTERVALS.YEAR
        subscription.plan.interval_count = 1
        subscription.plan.save()

        subscription.start_date = datetime.date(year=2015, month=2, day=2)
        subscription.trial_end = (subscription.start_date +
                                  datetime.timedelta(days=90))
        subscription.save()

        start_date = subscription.start_date
        assert start_date == subscription.bucket_start_date(
            reference_date=datetime.date(year=2015, month=2, day=2)
        )

        end_date = datetime.date(year=2015, month=5, day=3)
        assert end_date == subscription.bucket_end_date(
            reference_date=datetime.date(year=2015, month=2, day=2))

        start_date = datetime.date(year=2015, month=5, day=4)
        assert start_date == subscription.bucket_start_date(
            reference_date=datetime.date(year=2015, month=5, day=4))

        end_date = datetime.date(year=2015, month=12, day=31)
        assert end_date == subscription.bucket_end_date(
            reference_date=datetime.date(year=2015, month=5, day=5))

        start_date = datetime.date(year=2016, month=1, day=1)
        assert start_date == subscription.bucket_start_date(
            reference_date=datetime.date(year=2016, month=1, day=1))

        end_date = datetime.date(year=2016, month=12, day=31)
        assert end_date == subscription.bucket_end_date(
            reference_date=datetime.date(year=2016, month=12, day=31))

    def test_subscription_billing_cycle_intervals_1(self):
        """
        Every month, 16 days of trial
        separate_cycles_during_trial = True
        generate_documents_on_trial_end = False
        """

        subscription = SubscriptionFactory.create()
        metered_feature = MeteredFeatureFactory.create()

        subscription.plan.metered_features.add(metered_feature)

        start_date = datetime.date(year=2015, month=2, day=17)

        subscription.start_date = start_date
        subscription.trial_end = (subscription.start_date +
                                  datetime.timedelta(days=15))
        subscription.activate()
        subscription.save()

        subscription.plan.interval = Plan.INTERVALS.MONTH
        subscription.plan.interval_count = 1
        subscription.plan.separate_cycles_during_trial = True
        subscription.plan.generate_documents_on_trial_end = False
        subscription.plan.save()

        reference_date = start_date
        assert start_date == subscription.cycle_start_date(reference_date)

        end_date = datetime.date(year=2015, month=2, day=28)
        assert end_date == subscription.cycle_end_date(reference_date)

        start_date = datetime.date(year=2015, month=3, day=1)
        reference_date = start_date
        assert start_date == subscription.cycle_start_date(reference_date)

        end_date = datetime.date(year=2015, month=3, day=31)
        assert end_date == subscription.cycle_end_date(reference_date)

        start_date = datetime.date(year=2015, month=4, day=1)
        reference_date = start_date
        assert start_date == subscription.cycle_start_date(reference_date)

        end_date = datetime.date(year=2015, month=4, day=30)
        assert end_date == subscription.cycle_end_date(reference_date)

    def test_subscription_billing_cycle_intervals_2(self):
        """
        Every 2 months, 150 days of trial (2015-05-30)
        separate_cycles_during_trial = True
        generate_documents_on_trial_end = True
        """

        subscription = SubscriptionFactory.create()
        metered_feature = MeteredFeatureFactory.create()

        subscription.plan.metered_features.add(metered_feature)

        subscription.plan.interval = Plan.INTERVALS.MONTH
        subscription.plan.interval_count = 2
        subscription.plan.separate_cycles_during_trial = True
        subscription.plan.generate_documents_on_trial_end = True
        subscription.plan.save()

        subscription.start_date = datetime.date(year=2014, month=12, day=31)
        subscription.trial_end = (subscription.start_date +
                                  datetime.timedelta(days=150))
        subscription.activate()
        subscription.save()

        start_date = subscription.start_date
        reference_date = start_date
        assert start_date == subscription.cycle_start_date(reference_date)

        end_date = datetime.date(year=2014, month=12, day=31)
        assert end_date == subscription.cycle_end_date(reference_date)

        start_date = datetime.date(year=2015, month=1, day=1)
        reference_date = start_date
        assert start_date == subscription.cycle_start_date(reference_date)

        end_date = datetime.date(year=2015, month=2, day=28)
        assert end_date == subscription.cycle_end_date(reference_date)

        start_date = datetime.date(year=2015, month=3, day=1)
        reference_date = start_date
        assert start_date == subscription.cycle_start_date(reference_date)

        end_date = datetime.date(year=2015, month=4, day=30)
        assert end_date == subscription.cycle_end_date(reference_date)

        start_date = datetime.date(year=2015, month=5, day=1)
        reference_date = start_date
        assert start_date == subscription.cycle_start_date(reference_date)

        end_date = datetime.date(year=2015, month=5, day=30)  # trial end
        assert end_date == subscription.cycle_end_date(reference_date)

        start_date = datetime.date(year=2015, month=5, day=31)
        reference_date = start_date
        assert start_date == subscription.cycle_start_date(reference_date)

        end_date = datetime.date(year=2015, month=6, day=30)  # realigned to initial alignment
        assert end_date == subscription.cycle_end_date(reference_date)

        start_date = datetime.date(year=2015, month=7, day=1)
        reference_date = start_date
        assert start_date == subscription.cycle_start_date(reference_date)

        end_date = datetime.date(year=2015, month=8, day=31)
        assert end_date == subscription.cycle_end_date(reference_date)

    def test_subscription_billing_cycle_intervals_3(self):
        """
        Every 2 weeks, 8 days of trial
        separate_cycles_during_trial = True
        generate_documents_on_trial_end = True
        """

        subscription = SubscriptionFactory.create()
        metered_feature = MeteredFeatureFactory.create()

        subscription.plan.metered_features.add(metered_feature)

        subscription.plan.interval = Plan.INTERVALS.WEEK
        subscription.plan.interval_count = 2
        subscription.plan.separate_cycles_during_trial = True
        subscription.plan.generate_documents_on_trial_end = True
        subscription.plan.save()

        subscription.start_date = datetime.date(year=2015, month=5, day=31)
        subscription.trial_end = (subscription.start_date +
                                  datetime.timedelta(days=7))
        subscription.activate()
        subscription.save()

        start_date = subscription.start_date
        reference_date = start_date
        assert start_date == subscription.cycle_start_date(reference_date)

        end_date = datetime.date(year=2015, month=5, day=31)  # billing cycle alignment
        assert end_date == subscription.cycle_end_date(reference_date)

        start_date = datetime.date(year=2015, month=6, day=1)
        reference_date = start_date
        assert start_date == subscription.cycle_start_date(reference_date)

        end_date = datetime.date(year=2015, month=6, day=7)  # trial end
        assert end_date == subscription.cycle_end_date(reference_date)

        start_date = datetime.date(year=2015, month=6, day=8)
        reference_date = start_date
        assert start_date == subscription.cycle_start_date(reference_date)

        end_date = datetime.date(year=2015, month=6, day=14)  # cycle realignment after trial
        assert end_date == subscription.cycle_end_date(reference_date)

        start_date = datetime.date(year=2015, month=6, day=15)
        reference_date = start_date
        assert start_date == subscription.cycle_start_date(reference_date)

        end_date = datetime.date(year=2015, month=6, day=28)
        assert end_date == subscription.cycle_end_date(reference_date)

    def test_subscription_billing_cycle_intervals_4(self):
        """
        Every year, 90 days of trial
        separate_cycles_during_trial = True
        generate_documents_on_trial_end = False
        """

        subscription = SubscriptionFactory.create()
        metered_feature = MeteredFeatureFactory.create()

        subscription.plan.metered_features.add(metered_feature)

        subscription.plan.interval = Plan.INTERVALS.YEAR
        subscription.plan.interval_count = 1
        subscription.plan.separate_cycles_during_trial = True
        subscription.plan.generate_documents_on_trial_end = False
        subscription.plan.save()

        subscription.start_date = datetime.date(year=2015, month=2, day=2)
        subscription.trial_end = (subscription.start_date +
                                  datetime.timedelta(days=90))
        subscription.activate()
        subscription.save()

        start_date = subscription.start_date
        reference_date = start_date
        assert start_date == subscription.cycle_start_date(reference_date)

        end_date = datetime.date(year=2015, month=12, day=31)
        assert end_date == subscription.cycle_end_date(reference_date)

        start_date = datetime.date(year=2016, month=1, day=1)
        reference_date = start_date
        assert start_date == subscription.cycle_start_date(reference_date)

        end_date = datetime.date(year=2016, month=12, day=31)
        assert end_date == subscription.cycle_end_date(reference_date)


class TestSubscriptionShouldBeBilled(TestCase):
    """
    NOTE (important abbreviations):
        * sbb = should_be_billed
        * w = with
        * wa = without
        * cb = consolidated billing
    """

    def test_sub_canceled_at_end_of_bc_w_consolidated_billing(self):
        plan = PlanFactory.create(generate_after=120)
        subscription = SubscriptionFactory.create(
            plan=plan,
            state=Subscription.STATES.CANCELED,
            start_date=datetime.date(2015, 8, 22),
            cancel_date=datetime.date(2015, 9, 1)
        )
        correct_billing_date = datetime.date(2015, 9, 2)
        incorrect_billing_date = datetime.date(2015, 8, 22)

        true_property = PropertyMock(return_value=True)
        with patch.multiple(
            Subscription,
            _has_existing_customer_with_consolidated_billing=true_property
        ):
            assert subscription.should_be_billed(correct_billing_date) is True
            assert subscription.should_be_billed(incorrect_billing_date) is False

    def test_sub_canceled_now_w_consolidated_billing(self):
        plan = PlanFactory.create(generate_after=120)
        subscription = SubscriptionFactory.create(
            plan=plan,
            state=Subscription.STATES.CANCELED,
            start_date=datetime.date(2015, 8, 10),
            cancel_date=datetime.date(2015, 8, 22)
        )
        billing_date_1 = datetime.date(2015, 9, 1)
        billing_date_2 = datetime.date(2015, 8, 23)

        true_property = PropertyMock(return_value=True)
        with patch.multiple(
            Subscription,
            _has_existing_customer_with_consolidated_billing=true_property
        ):
            assert subscription.should_be_billed(billing_date_1) is True
            assert subscription.should_be_billed(billing_date_2) is True

    def test_canceled_sub_wa_consolidated_billing(self):
        plan = PlanFactory.create(generate_after=120)
        subscription = SubscriptionFactory.create(
            plan=plan,
            state=Subscription.STATES.CANCELED,
            start_date=datetime.date(2015, 8, 10),
            cancel_date=datetime.date(2015, 8, 22)
        )
        correct_billing_date = datetime.date(2015, 8, 23)

        false_property = PropertyMock(return_value=False)
        with patch.multiple(
            Subscription,
            _has_existing_customer_with_consolidated_billing=false_property
        ):
            assert subscription.should_be_billed(correct_billing_date) is True

    def test_canceled_sub_w_date_before_cancel_date(self):
        plan = PlanFactory.create(generate_after=120)
        subscription = SubscriptionFactory.create(
            plan=plan,
            state=Subscription.STATES.CANCELED,
            cancel_date=datetime.date(2015, 8, 22),
            start_date=datetime.date(2015, 8, 1)
        )
        incorrect_billing_date = datetime.date(2015, 8, 10)

        assert subscription.should_be_billed(incorrect_billing_date) is False

    def test_new_active_sub_no_trial_w_consolidated_billing(self):
        plan = PlanFactory.create(generate_after=120)
        subscription = SubscriptionFactory.create(
            plan=plan,
            state=Subscription.STATES.ACTIVE,
            start_date=datetime.date(2015, 8, 12)
        )
        incorrect_billing_date = datetime.date(2015, 8, 11)
        correct_billing_date = datetime.date(2015, 8, 12)

        true_property = PropertyMock(return_value=True)
        mocked_bucket_end_date = MagicMock(
            return_value=datetime.date(2015, 8, 31)
        )
        with patch.multiple(
            Subscription,
            _has_existing_customer_with_consolidated_billing=true_property,
            is_billed_first_time=true_property,
            bucket_end_date=mocked_bucket_end_date,
        ):
            assert subscription.should_be_billed(correct_billing_date) is True
            assert subscription.should_be_billed(incorrect_billing_date) is False

    def test_new_active_sub_no_trial_wa_consolidated_billing(self):
        plan = PlanFactory.create(generate_after=120)
        subscription = SubscriptionFactory.create(
            plan=plan,
            state=Subscription.STATES.ACTIVE,
            start_date=datetime.date(2015, 8, 12)
        )
        correct_billing_date_1 = datetime.date(2015, 8, 12)
        correct_billing_date_2 = datetime.date(2015, 8, 20)

        true_property = PropertyMock(return_value=True)
        false_property = PropertyMock(return_value=False)
        with patch.multiple(
            Subscription,
            is_billed_first_time=true_property,
            _has_existing_customer_with_consolidated_billing=false_property,
        ):
            assert subscription.should_be_billed(correct_billing_date_1) is True
            assert subscription.should_be_billed(correct_billing_date_2) is True

    def test_new_active_sub_with_smaller_billing_date_than_start_date(self):
        plan = PlanFactory.create(generate_after=120)
        subscription = SubscriptionFactory.create(
            plan=plan,
            state=Subscription.STATES.ACTIVE,
            start_date=datetime.date(2015, 8, 22)
        )
        billing_date = datetime.date(2015, 8, 10)

        assert subscription.should_be_billed(billing_date) is False

    def test_new_active_sub_trial_end_same_month_as_start_date_w_cb(self):
        plan = PlanFactory.create(generate_after=100)
        subscription = SubscriptionFactory.create(
            plan=plan,
            state=Subscription.STATES.ACTIVE,
            start_date=datetime.date(2015, 8, 12),
            trial_end=datetime.date(2015, 8, 26)
        )
        correct_billing_date_1 = datetime.date(2015, 9, 1)
        correct_billing_date_2 = datetime.date(2015, 8, 12)
        incorrect_billing_date_1 = datetime.date(2015, 8, 11)
        incorrect_billing_date_2 = datetime.date(2015, 7, 11)

        true_property = PropertyMock(return_value=True)
        with patch.multiple(
            Subscription,
            is_billed_first_time=true_property,
            _has_existing_customer_with_consolidated_billing=true_property,
        ):
            assert subscription.should_be_billed(correct_billing_date_1) is True
            assert subscription.should_be_billed(correct_billing_date_2) is True
            assert subscription.should_be_billed(incorrect_billing_date_1) is False
            assert subscription.should_be_billed(incorrect_billing_date_2) is False

    def test_new_active_sub_trial_end_same_month_as_start_date_wa_cb(self):
        plan = PlanFactory.create(generate_after=100)
        subscription = SubscriptionFactory.create(
            plan=plan,
            state=Subscription.STATES.ACTIVE,
            start_date=datetime.date(2015, 8, 12),
            trial_end=datetime.date(2015, 8, 26)
        )
        correct_billing_date_1 = datetime.date(2015, 8, 27)
        correct_billing_date_2 = datetime.date(2015, 8, 12)
        incorrect_billing_date = datetime.date(2015, 8, 11)

        true_property = PropertyMock(return_value=True)
        false_property = PropertyMock(return_value=False)
        mocked_bucket_end_date = MagicMock(
            return_value=datetime.date(2015, 8, 26)
        )
        with patch.multiple(
            Subscription,
            is_billed_first_time=true_property,
            _has_existing_customer_with_consolidated_billing=false_property,
            bucket_end_date=mocked_bucket_end_date
        ):
            assert subscription.should_be_billed(correct_billing_date_1) is True
            assert subscription.should_be_billed(correct_billing_date_2) is True
            assert subscription.should_be_billed(incorrect_billing_date) is False

    def test_new_active_sub_trial_end_different_month_from_start_date_w_cb(self):
        plan = PlanFactory.create(generate_after=100)
        subscription = SubscriptionFactory.create(
            plan=plan,
            state=Subscription.STATES.ACTIVE,
            start_date=datetime.date(2015, 8, 12),
            trial_end=datetime.date(2015, 9, 12)
        )
        correct_billing_date_1 = datetime.date(2015, 9, 1)
        correct_billing_date_2 = datetime.date(2015, 8, 12)
        incorrect_billing_date_1 = datetime.date(2015, 8, 11)
        incorrect_billing_date_2 = datetime.date(2015, 7, 3)

        true_property = PropertyMock(return_value=True)
        mocked_bucket_end_date = MagicMock(
            return_value=datetime.date(2015, 8, 31)
        )
        with patch.multiple(
            Subscription,
            is_billed_first_time=true_property,
            _has_existing_customer_with_consolidated_billing=true_property,
            bucket_end_date=mocked_bucket_end_date
        ):
            assert subscription.should_be_billed(correct_billing_date_1) is True
            assert subscription.should_be_billed(correct_billing_date_2) is True
            assert subscription.should_be_billed(incorrect_billing_date_1) is False
            assert subscription.should_be_billed(incorrect_billing_date_2) is False

    def test_already_billed_sub_w_cb_on_trial_last_billing_date(self):
        plan = PlanFactory.create(generate_after=100)
        subscription = SubscriptionFactory.create(
            plan=plan,
            state=Subscription.STATES.ACTIVE,
            start_date=datetime.date(2015, 8, 12),
            trial_end=datetime.date(2015, 9, 12)
        )
        correct_billing_date_1 = datetime.date(2015, 10, 1)
        correct_billing_date_2 = datetime.date(2015, 9, 12)
        correct_billing_date_3 = datetime.date(2015, 8, 12)
        incorrect_billing_date = datetime.date(2015, 8, 11)

        true_property = PropertyMock(return_value=True)
        false_property = PropertyMock(return_value=False)
        mocked_on_trial = MagicMock(return_value=True)
        mocked_last_billing_date = PropertyMock(
            return_value=datetime.date(2015, 9, 2)
        )
        with patch.multiple(
            Subscription,
            is_billed_first_time=false_property,
            on_trial=mocked_on_trial,
            last_billing_date=mocked_last_billing_date,
            _has_existing_customer_with_consolidated_billing=true_property,
        ):
            assert subscription.should_be_billed(correct_billing_date_1) is True
            assert subscription.should_be_billed(correct_billing_date_2) is True
            assert subscription.should_be_billed(correct_billing_date_3) is True
            assert subscription.should_be_billed(incorrect_billing_date) is False

    def test_already_billed_sub_wa_cb_on_trial_last_billing_date(self):
        plan = PlanFactory.create(generate_after=100,
                                  interval=Plan.INTERVALS.MONTH,
                                  interval_count=1)
        subscription = SubscriptionFactory.create(
            plan=plan,
            state=Subscription.STATES.ACTIVE,
            start_date=datetime.date(2015, 8, 12),
            trial_end=datetime.date(2015, 9, 12)
        )
        correct_billing_date = datetime.date(2015, 8, 12)
        incorrect_billing_date_1 = datetime.date(2015, 8, 11)

        false_property = PropertyMock(return_value=False)
        mocked_on_trial = MagicMock(return_value=True)
        mocked_last_billing_date = PropertyMock(
            return_value=datetime.date(2015, 9, 2)
        )
        mocked_bucket_end_date = MagicMock(
            return_value=datetime.date(2015, 9, 12)
        )
        with patch.multiple(
            Subscription,
            is_billed_first_time=false_property,
            on_trial=mocked_on_trial,
            last_billing_date=mocked_last_billing_date,
            _has_existing_customer_with_consolidated_billing=false_property,
            bucket_end_date=mocked_bucket_end_date
        ):
            assert subscription.should_be_billed(correct_billing_date) is True
            assert subscription.should_be_billed(incorrect_billing_date_1) is False

    def test_already_billed_sub_wa_cb(self):
        plan = PlanFactory.create(generate_after=100,
                                  interval=Plan.INTERVALS.MONTH,
                                  interval_count=1)
        subscription = SubscriptionFactory.create(
            plan=plan,
            state=Subscription.STATES.ACTIVE,
            start_date=datetime.date(2015, 1, 1)
        )
        correct_billing_date = datetime.date(2015, 10, 1)
        incorrect_billing_date_1 = datetime.date(2015, 9, 3)
        incorrect_billing_date_2 = datetime.date(2015, 9, 12)
        incorrect_billing_date_3 = datetime.date(2015, 9, 30)

        BillingLog.objects.create(subscription=subscription,
                                  billing_date=datetime.date(2015, 9, 2),
                                  plan_billed_up_to=datetime.date(2015, 9, 30),
                                  metered_features_billed_up_to=datetime.date(2015, 9, 2))

        assert subscription.should_be_billed(correct_billing_date) is True
        assert subscription.should_be_billed(incorrect_billing_date_1) is False
        assert subscription.should_be_billed(incorrect_billing_date_2) is False
        assert subscription.should_be_billed(incorrect_billing_date_3) is False

    def test_canceled_sub_with_billed_plan_but_not_metered_features_1(self):
        plan = PlanFactory.create(generate_after=100,
                                  interval=Plan.INTERVALS.MONTH,
                                  interval_count=1)
        subscription = SubscriptionFactory.create(
            plan=plan,
            state=Subscription.STATES.CANCELED,
            start_date=datetime.date(2015, 1, 1),
            cancel_date=datetime.date(2018, 1, 20)
        )

        billing_log = BillingLog.objects.create(
            subscription=subscription,
            billing_date=datetime.date(2015, 9, 2),
            plan_billed_up_to=datetime.date(2018, 1, 31),
            metered_features_billed_up_to=datetime.date(2017, 12, 31)
        )

        correct_billing_date_1 = subscription.cancel_date + datetime.timedelta(days=1)
        correct_billing_date_2 = datetime.date(2018, 2, 1)
        incorrect_billing_date = correct_billing_date_1 - datetime.timedelta(days=1)

        assert \
            billing_log.metered_features_billed_up_to \
            < incorrect_billing_date \
            <= subscription.cancel_date \
            < correct_billing_date_1 \
            < billing_log.plan_billed_up_to \
            < correct_billing_date_2 \

        assert subscription.should_be_billed(correct_billing_date_1)
        assert subscription.should_be_billed(correct_billing_date_2)
        assert not subscription.should_be_billed(incorrect_billing_date)

    def test_canceled_sub_with_billed_plan_but_not_metered_features_2(self):
        # Like previous test, but this time there's cycle_billing_duration added to the mix
        plan = PlanFactory.create(generate_after=100,
                                  interval=Plan.INTERVALS.MONTH,
                                  interval_count=1,
                                  cycle_billing_duration=datetime.timedelta(days=5))

        subscription = SubscriptionFactory.create(
            plan=plan,
            state=Subscription.STATES.CANCELED,
            start_date=datetime.date(2015, 1, 1),
            cancel_date=datetime.date(2018, 1, 20)
        )

        billing_log = BillingLog.objects.create(
            subscription=subscription,
            billing_date=datetime.date(2015, 9, 2),
            plan_billed_up_to=datetime.date(2018, 1, 31),
            metered_features_billed_up_to=datetime.date(2017, 12, 31)
        )

        correct_billing_date = datetime.date(2018, 2, 1)
        incorrect_billing_date_1 = subscription.cancel_date + datetime.timedelta(days=1)
        incorrect_billing_date_2 = correct_billing_date - datetime.timedelta(days=1)

        assert \
            billing_log.metered_features_billed_up_to \
            < subscription.cancel_date \
            < incorrect_billing_date_1 \
            < incorrect_billing_date_2 \
            <= billing_log.plan_billed_up_to \
            < correct_billing_date

        assert subscription.should_be_billed(correct_billing_date)
        assert not subscription.should_be_billed(incorrect_billing_date_1)
        assert not subscription.should_be_billed(incorrect_billing_date_2)

    @freeze_time('2015-01-01')
    def test_updateable_buckets_active_subscription(self):
        plan = PlanFactory.create(generate_after=24 * 60,
                                  interval=Plan.INTERVALS.MONTH,
                                  interval_count=1)
        subscription = SubscriptionFactory.create(
            plan=plan,
            state=Subscription.STATES.ACTIVE,
            start_date=datetime.date(2015, 1, 1)
        )
        assert subscription.updateable_buckets() == [
            {'start_date': datetime.date(2015, 1, 1), 'end_date': datetime.date(2015, 1, 31)},
        ]

    @freeze_time('2015-01-01')
    def test_updateable_buckets_2_months_active_subscription(self):
        plan = PlanFactory.create(generate_after=24 * 60,
                                  interval=Plan.INTERVALS.MONTH,
                                  interval_count=1)
        subscription = SubscriptionFactory.create(
            plan=plan,
            state=Subscription.STATES.ACTIVE,
            start_date=datetime.date(2014, 1, 1)
        )
        assert subscription.updateable_buckets() == [
            {'start_date': datetime.date(2015, 1, 1), 'end_date': datetime.date(2015, 1, 31)},
            {'start_date': datetime.date(2014, 12, 1), 'end_date': datetime.date(2014, 12, 31)},
        ]

    @freeze_time('2015-01-01')
    def test_updateable_buckets_2_months_canceled_subscription_at_end_of_month(self):
        plan = PlanFactory.create(generate_after=24 * 60,
                                  interval=Plan.INTERVALS.MONTH,
                                  interval_count=1)
        subscription = SubscriptionFactory.create(
            plan=plan,
            state=Subscription.STATES.CANCELED,
            start_date=datetime.date(2015, 1, 1),
            cancel_date=datetime.date(2015, 1, 31)
        )
        assert subscription.updateable_buckets() == [
            {'start_date': datetime.date(2015, 1, 1), 'end_date': datetime.date(2015, 1, 31)},
        ]

    @freeze_time('2015-01-01')
    def test_updateable_buckets_2_months_canceled_subscription_last_month(self):
        plan = PlanFactory.create(generate_after=24 * 60,
                                  interval=Plan.INTERVALS.MONTH,
                                  interval_count=1)
        subscription = SubscriptionFactory.create(
            plan=plan,
            state=Subscription.STATES.CANCELED,
            start_date=datetime.date(2014, 1, 1),
            cancel_date=datetime.date(2014, 12, 31)
        )
        assert subscription.updateable_buckets() == []
