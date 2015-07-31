import datetime

from django.test import TestCase
from mock import patch

from silver.models import Plan
from silver.tests.factories import (SubscriptionFactory, MeteredFeatureFactory)


class TestSubscription(TestCase):
    def test_subscription_mf_units_log_intervals(self):
        subscription = SubscriptionFactory.create()
        metered_feature = MeteredFeatureFactory.create()

        subscription.plan.metered_features.add(metered_feature)

        subscription.start_date = datetime.date(year=2015, month=2, day=17)
        subscription.activate()
        subscription.save()

        # Every month, 16 days of trial
        subscription.plan.interval = Plan.INTERVALS.MONTH
        subscription.plan.interval_count = 1
        subscription.plan.save()

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

        # Every 2 months, 5 months of trial (2015-05-30)
        subscription.plan.interval = Plan.INTERVALS.MONTH
        subscription.plan.interval_count = 2
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

        # Every 2 weeks, 8 days of trial
        subscription.plan.interval = Plan.INTERVALS.WEEK
        subscription.plan.interval_count = 2
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

        # Every year, 3 months (90 days) of trial
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

    def test_subscription_billing_cycle_intervals(self):
        subscription = SubscriptionFactory.create()
        metered_feature = MeteredFeatureFactory.create()

        subscription.plan.metered_features.add(metered_feature)

        start_date = datetime.date(year=2015, month=2, day=17)

        subscription.start_date = start_date
        subscription.activate()
        subscription.save()

        with patch('silver.models.timezone') as mock_timezone:
            # Every month, 16 days of trial
            subscription.plan.interval = Plan.INTERVALS.MONTH
            subscription.plan.interval_count = 1
            subscription.plan.save()

            subscription.trial_end = (subscription.start_date +
                                      datetime.timedelta(days=15))
            mock_timezone.now.return_value = datetime.datetime.combine(
                start_date, datetime.datetime.min.time())
            assert start_date == subscription.current_start_date

            end_date = datetime.date(year=2015, month=2, day=28)
            assert end_date == subscription.current_end_date

            start_date = datetime.date(year=2015, month=3, day=1)
            mock_timezone.now.return_value = datetime.datetime.combine(
                start_date, datetime.datetime.min.time())
            assert start_date == subscription.current_start_date

            end_date = datetime.date(year=2015, month=3, day=31)
            assert end_date == subscription.current_end_date

            start_date = datetime.date(year=2015, month=4, day=1)
            mock_timezone.now.return_value = datetime.datetime.combine(
                start_date, datetime.datetime.min.time())
            assert start_date == subscription.current_start_date

            end_date = datetime.date(year=2015, month=4, day=30)
            assert end_date == subscription.current_end_date

            # Every 2 months, 5 months of trial (2015-05-30)
            subscription.plan.interval = Plan.INTERVALS.MONTH
            subscription.plan.interval_count = 2
            subscription.plan.save()

            subscription.start_date = datetime.date(year=2014, month=12, day=31)
            subscription.trial_end = (subscription.start_date +
                                      datetime.timedelta(days=150))
            subscription.save()

            start_date = subscription.start_date
            mock_timezone.now.return_value = datetime.datetime.combine(
                start_date, datetime.datetime.min.time())
            assert start_date == subscription.current_start_date

            end_date = datetime.date(year=2014, month=12, day=31)
            assert end_date == subscription.current_end_date

            start_date = datetime.date(year=2015, month=1, day=1)
            mock_timezone.now.return_value = datetime.datetime.combine(
                start_date, datetime.datetime.min.time())
            assert start_date == subscription.current_start_date

            end_date = datetime.date(year=2015, month=2, day=28)
            assert end_date == subscription.current_end_date

            start_date = datetime.date(year=2015, month=3, day=1)
            mock_timezone.now.return_value = datetime.datetime.combine(
                start_date, datetime.datetime.min.time())
            assert start_date == subscription.current_start_date

            end_date = datetime.date(year=2015, month=4, day=30)
            assert end_date == subscription.current_end_date

            start_date = datetime.date(year=2015, month=5, day=1)
            mock_timezone.now.return_value = datetime.datetime.combine(
                start_date, datetime.datetime.min.time())
            assert start_date == subscription.current_start_date

            end_date = datetime.date(year=2015, month=6, day=30)
            assert end_date == subscription.current_end_date

            start_date = datetime.date(year=2015, month=7, day=1)
            mock_timezone.now.return_value = datetime.datetime.combine(
                start_date, datetime.datetime.min.time())
            assert start_date == subscription.current_start_date

            end_date = datetime.date(year=2015, month=8, day=31)
            assert end_date == subscription.current_end_date

            # Every 2 weeks, 8 days of trial
            subscription.plan.interval = Plan.INTERVALS.WEEK
            subscription.plan.interval_count = 2
            subscription.plan.save()

            subscription.start_date = datetime.date(year=2015, month=5, day=31)
            subscription.trial_end = (subscription.start_date +
                                      datetime.timedelta(days=7))
            subscription.save()

            start_date = subscription.start_date
            mock_timezone.now.return_value = datetime.datetime.combine(
                start_date, datetime.datetime.min.time())
            assert start_date == subscription.current_start_date

            end_date = datetime.date(year=2015, month=5, day=31)
            assert end_date == subscription.current_end_date

            start_date = datetime.date(year=2015, month=6, day=1)
            mock_timezone.now.return_value = datetime.datetime.combine(
                start_date, datetime.datetime.min.time())
            assert start_date == subscription.current_start_date

            end_date = datetime.date(year=2015, month=6, day=14)
            assert end_date == subscription.current_end_date

            start_date = datetime.date(year=2015, month=6, day=15)
            mock_timezone.now.return_value = datetime.datetime.combine(
                start_date, datetime.datetime.min.time())
            assert start_date == subscription.current_start_date

            end_date = datetime.date(year=2015, month=6, day=28)
            assert end_date == subscription.current_end_date

            # Every year, 3 months (90 days) of trial
            subscription.plan.interval = Plan.INTERVALS.YEAR
            subscription.plan.interval_count = 1
            subscription.plan.save()

            subscription.start_date = datetime.date(year=2015, month=2, day=2)
            subscription.trial_end = (subscription.start_date +
                                      datetime.timedelta(days=90))
            subscription.save()

            start_date = subscription.start_date
            mock_timezone.now.return_value = datetime.datetime.combine(
                start_date, datetime.datetime.min.time())
            assert start_date == subscription.current_start_date

            end_date = datetime.date(year=2015, month=12, day=31)
            assert end_date == subscription.current_end_date

            start_date = datetime.date(year=2016, month=1, day=1)
            mock_timezone.now.return_value = datetime.datetime.combine(
                start_date, datetime.datetime.min.time())
            assert start_date == subscription.current_start_date

            end_date = datetime.date(year=2016, month=12, day=31)
            assert end_date == subscription.current_end_date

    def test_should_be_billed(self):
        assert True
