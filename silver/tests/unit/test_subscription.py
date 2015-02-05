import datetime as dt

from django.utils import timezone
from django.test import TestCase
from mock import MagicMock, patch

from silver.tests.factories import SubscriptionFactory

class TestSubscriptionModel(TestCase):

    def test_first_billing_one_year_interval(self):
        test_year = 2015
        current_tz = timezone.get_current_timezone()
        test_date = dt.datetime(test_year, 5, 5, tzinfo=current_tz)
        mocked_timezone_now = MagicMock()
        mocked_timezone_now.return_value = test_date

        with patch('silver.models.timezone.now', mocked_timezone_now):
            subscription = SubscriptionFactory.create()

            subscription.start_date = dt.date(test_year - 1, 2, 5)
            subscription.plan.generate_after = 0
            subscription.plan.interval = 'year'
            subscription.plan.interval_count = 1
            subscription.save()

            assert subscription.should_be_billed == True

    def test_first_billing_one_year_interval_over_limit(self):
        test_year = 2015
        current_tz = timezone.get_current_timezone()
        test_date = dt.datetime(test_year, 1, 2, tzinfo=current_tz)
        mocked_timezone_now = MagicMock()
        mocked_timezone_now.return_value = test_date

        with patch('silver.models.timezone.now', mocked_timezone_now):
            subscription = SubscriptionFactory.create()

            subscription.start_date = dt.date(test_year - 1, 1, 1)
            subscription.plan.generate_after = 0
            subscription.plan.interval = 'year'
            subscription.plan.interval_count = 1
            subscription.save()

            assert subscription.should_be_billed == True

    def test_first_billing_one_year_interval_limit(self):
        test_year = 2015
        current_tz = timezone.get_current_timezone()
        test_date = dt.datetime(test_year, 1, 1, tzinfo=current_tz)
        mocked_timezone_now = MagicMock()
        mocked_timezone_now.return_value = test_date

        with patch('silver.models.timezone.now', mocked_timezone_now):
            subscription = SubscriptionFactory.create()

            subscription.start_date = dt.date(test_year - 1, 1, 1)
            subscription.plan.generate_after = 0
            subscription.plan.interval = 'year'
            subscription.plan.interval_count = 1
            subscription.save()

            assert subscription.should_be_billed == False

    def test_first_billing_two_years_interval(self):
        test_year = 2015
        current_tz = timezone.get_current_timezone()
        test_date = dt.datetime(test_year, 5, 5, tzinfo=current_tz)
        mocked_timezone_now = MagicMock()
        mocked_timezone_now.return_value = test_date

        with patch('silver.models.timezone.now', mocked_timezone_now):
            subscription = SubscriptionFactory.create()

            subscription.start_date = dt.date(test_year - 2, 5, 5)
            subscription.plan.generate_after = 0
            subscription.plan.interval = 'year'
            subscription.plan.interval_count = 2
            subscription.save()

            assert subscription.should_be_billed == True

    def test_first_billing_two_years_interval_limit(self):
        test_year = 2015
        current_tz = timezone.get_current_timezone()
        test_date = dt.datetime(test_year, 1, 1, tzinfo=current_tz)
        mocked_timezone_now = MagicMock()
        mocked_timezone_now.return_value = test_date

        with patch('silver.models.timezone.now', mocked_timezone_now):
            subscription = SubscriptionFactory.create()

            subscription.start_date = dt.date(test_year - 2, 1, 1)
            subscription.plan.generate_after = 0
            subscription.plan.interval = 'year'
            subscription.plan.interval_count = 2
            subscription.save()

            assert subscription.should_be_billed == False

    def test_first_billing_two_years_interval_over_limit(self):
        test_year = 2015
        current_tz = timezone.get_current_timezone()
        test_date = dt.datetime(test_year, 5, 5, tzinfo=current_tz)
        mocked_timezone_now = MagicMock()
        mocked_timezone_now.return_value = test_date

        with patch('silver.models.timezone.now', mocked_timezone_now):
            subscription = SubscriptionFactory.create()

            subscription.start_date = dt.date(test_year - 2, 1, 2)
            subscription.plan.generate_after = 0
            subscription.plan.interval = 'year'
            subscription.plan.interval_count = 2
            subscription.save()

            assert subscription.should_be_billed == True

    def test_first_billing_two_years_interval_below_limit(self):
        test_year = 2014
        current_tz = timezone.get_current_timezone()
        test_date = dt.datetime(test_year, 12, 31, tzinfo=current_tz)
        mocked_timezone_now = MagicMock()
        mocked_timezone_now.return_value = test_date

        with patch('silver.models.timezone.now', mocked_timezone_now):
            subscription = SubscriptionFactory.create()

            subscription.start_date = dt.date(test_year - 2, 1, 2)
            subscription.plan.generate_after = 0
            subscription.plan.interval = 'year'
            subscription.plan.interval_count = 2
            subscription.save()

            assert subscription.should_be_billed == True

    def test_first_billing_pass_year_interval(self):
        test_year = 2015
        current_tz = timezone.get_current_timezone()
        test_date = dt.datetime(test_year, 5, 5, tzinfo=current_tz)
        mocked_timezone_now = MagicMock()
        mocked_timezone_now.return_value = test_date

        with patch('silver.models.timezone.now', mocked_timezone_now):
            subscription = SubscriptionFactory.create()

            subscription.start_date = dt.date(test_year, 2, 5)
            subscription.plan.generate_after = 0
            subscription.plan.interval = 'year'
            subscription.plan.interval_count = 2
            subscription.save()

            assert subscription.should_be_billed == False

    def test_first_billing_one_month_interval(self):
        test_year = 2015
        test_month = 2
        current_tz = timezone.get_current_timezone()
        test_date = dt.datetime(test_year, test_month, 2, tzinfo=current_tz)
        mocked_timezone_now = MagicMock()
        mocked_timezone_now.return_value = test_date

        with patch('silver.models.timezone.now', mocked_timezone_now):
            subscription = SubscriptionFactory.create()

            subscription.start_date = dt.date(test_year, test_month - 1, 5)
            subscription.plan.generate_after = 0
            subscription.plan.interval = 'month'
            subscription.plan.interval_count = 1
            subscription.save()

            assert subscription.should_be_billed == True

    def test_first_billing_one_month_interval_limit(self):
        test_year = 2015
        test_month = 2
        current_tz = timezone.get_current_timezone()
        test_date = dt.datetime(test_year, test_month, 1, tzinfo=current_tz)
        mocked_timezone_now = MagicMock()
        mocked_timezone_now.return_value = test_date

        with patch('silver.models.timezone.now', mocked_timezone_now):
            subscription = SubscriptionFactory.create()

            subscription.start_date = dt.date(test_year, test_month - 1, 1)
            subscription.plan.generate_after = 0
            subscription.plan.interval = 'month'
            subscription.plan.interval_count = 1
            subscription.save()

            assert subscription.should_be_billed == False

    def test_first_billing_one_month_below_limit(self):
        test_year = 2015
        test_month = 2
        current_tz = timezone.get_current_timezone()
        test_date = dt.datetime(test_year, test_month, 1, tzinfo=current_tz)
        mocked_timezone_now = MagicMock()
        mocked_timezone_now.return_value = test_date

        with patch('silver.models.timezone.now', mocked_timezone_now):
            subscription = SubscriptionFactory.create()

            subscription.start_date = dt.date(test_year, test_month, 10)
            subscription.plan.generate_after = 0
            subscription.plan.interval = 'month'
            subscription.plan.interval_count = 1
            subscription.save()

            assert subscription.should_be_billed == False

    def test_first_billing_two_months_interval(self):
        test_year = 2015
        test_month = 3
        current_tz = timezone.get_current_timezone()
        test_date = dt.datetime(test_year, test_month, 2, tzinfo=current_tz)
        mocked_timezone_now = MagicMock()
        mocked_timezone_now.return_value = test_date

        with patch('silver.models.timezone.now', mocked_timezone_now):
            subscription = SubscriptionFactory.create()

            subscription.start_date = dt.date(test_year, test_month - 2, 5)
            subscription.plan.generate_after = 0
            subscription.plan.interval = 'month'
            subscription.plan.interval_count = 2
            subscription.save()

            assert subscription.should_be_billed == True

    def test_first_billing_two_months_interval_limit(self):
        test_year = 2015
        test_month = 3
        current_tz = timezone.get_current_timezone()
        test_date = dt.datetime(test_year, test_month, 1, tzinfo=current_tz)
        mocked_timezone_now = MagicMock()
        mocked_timezone_now.return_value = test_date

        with patch('silver.models.timezone.now', mocked_timezone_now):
            subscription = SubscriptionFactory.create()

            subscription.start_date = dt.date(test_year, test_month - 2, 5)
            subscription.plan.generate_after = 0
            subscription.plan.interval = 'month'
            subscription.plan.interval_count = 2
            subscription.save()

            assert subscription.should_be_billed == False

    def test_first_billing_two_months_interval_below_limit(self):
        test_year = 2015
        test_month = 3
        current_tz = timezone.get_current_timezone()
        test_date = dt.datetime(test_year, test_month - 1, 1, tzinfo=current_tz)
        mocked_timezone_now = MagicMock()
        mocked_timezone_now.return_value = test_date

        with patch('silver.models.timezone.now', mocked_timezone_now):
            subscription = SubscriptionFactory.create()

            subscription.start_date = dt.date(test_year, test_month - 2, 5)
            subscription.plan.generate_after = 0
            subscription.plan.interval = 'month'
            subscription.plan.interval_count = 2
            subscription.save()

            assert subscription.should_be_billed == False

    def test_first_billing_one_week_interval(self):
        test_year = 2015
        test_month = 2
        current_tz = timezone.get_current_timezone()
        test_date = dt.datetime(test_year, test_month, 3, tzinfo=current_tz)
        mocked_timezone_now = MagicMock()
        mocked_timezone_now.return_value = test_date

        with patch('silver.models.timezone.now', mocked_timezone_now):
            subscription = SubscriptionFactory.create()

            subscription.start_date = dt.date(test_year, test_month, 1)
            subscription.plan.generate_after = 0
            subscription.plan.interval = 'week'
            subscription.plan.interval_count = 1
            subscription.save()

            assert subscription.should_be_billed == True

    def test_first_billing_one_week_interval_limit(self):
        test_year = 2015
        test_month = 2
        current_tz = timezone.get_current_timezone()
        test_date = dt.datetime(test_year, test_month, 2, tzinfo=current_tz)
        mocked_timezone_now = MagicMock()
        mocked_timezone_now.return_value = test_date

        with patch('silver.models.timezone.now', mocked_timezone_now):
            subscription = SubscriptionFactory.create()

            subscription.start_date = dt.date(test_year, test_month, 1)
            subscription.plan.generate_after = 0
            subscription.plan.interval = 'week'
            subscription.plan.interval_count = 1
            subscription.save()

            assert subscription.should_be_billed == False

    def test_first_billing_one_week_interval_below_limit(self):
        test_year = 2015
        test_month = 2
        current_tz = timezone.get_current_timezone()
        test_date = dt.datetime(test_year, test_month, 1, tzinfo=current_tz)
        mocked_timezone_now = MagicMock()
        mocked_timezone_now.return_value = test_date

        with patch('silver.models.timezone.now', mocked_timezone_now):
            subscription = SubscriptionFactory.create()

            subscription.start_date = dt.date(test_year, test_month, 1)
            subscription.plan.generate_after = 0
            subscription.plan.interval = 'week'
            subscription.plan.interval_count = 1
            subscription.save()

            assert subscription.should_be_billed == False

    def test_first_billing_two_weeks_interval(self):
        test_year = 2015
        test_month = 2
        current_tz = timezone.get_current_timezone()
        test_date = dt.datetime(test_year, test_month, 10, tzinfo=current_tz)
        mocked_timezone_now = MagicMock()
        mocked_timezone_now.return_value = test_date

        with patch('silver.models.timezone.now', mocked_timezone_now):
            subscription = SubscriptionFactory.create()

            subscription.start_date = dt.date(test_year, test_month, 1)
            subscription.plan.generate_after = 0
            subscription.plan.interval = 'week'
            subscription.plan.interval_count = 2
            subscription.save()

            assert subscription.should_be_billed == True

    def test_first_billing_two_weeks_interval_limit(self):
        test_year = 2015
        test_month = 2
        current_tz = timezone.get_current_timezone()
        test_date = dt.datetime(test_year, test_month, 9, tzinfo=current_tz)
        mocked_timezone_now = MagicMock()
        mocked_timezone_now.return_value = test_date

        with patch('silver.models.timezone.now', mocked_timezone_now):
            subscription = SubscriptionFactory.create()

            subscription.start_date = dt.date(test_year, test_month, 1)
            subscription.plan.generate_after = 0
            subscription.plan.interval = 'week'
            subscription.plan.interval_count = 2
            subscription.save()

            assert subscription.should_be_billed == False

    def test_first_billing_two_weeks_interval_below_limit(self):
        test_year = 2015
        test_month = 2
        current_tz = timezone.get_current_timezone()
        test_date = dt.datetime(test_year, test_month, 8, tzinfo=current_tz)
        mocked_timezone_now = MagicMock()
        mocked_timezone_now.return_value = test_date

        with patch('silver.models.timezone.now', mocked_timezone_now):
            subscription = SubscriptionFactory.create()

            subscription.start_date = dt.date(test_year, test_month, 1)
            subscription.plan.generate_after = 0
            subscription.plan.interval = 'week'
            subscription.plan.interval_count = 2
            subscription.save()

            assert subscription.should_be_billed == False

    def test_first_billing_one_day_interval(self):
        test_year = 2015
        test_month = 2
        current_tz = timezone.get_current_timezone()
        test_date = dt.datetime(test_year, test_month, 2, 0, 0, 2,
                                tzinfo=current_tz)
        mocked_timezone_now = MagicMock()
        mocked_timezone_now.return_value = test_date

        with patch('silver.models.timezone.now', mocked_timezone_now):
            subscription = SubscriptionFactory.create()

            subscription.start_date = dt.date(test_year, test_month, 1)
            subscription.plan.generate_after = 0
            subscription.plan.interval = 'day'
            subscription.plan.interval_count = 1
            subscription.save()

            assert subscription.should_be_billed == True

    def test_first_billing_one_day_interval_positive_generate_after_fail(self):
        test_year = 2015
        test_month = 2
        current_tz = timezone.get_current_timezone()
        test_date = dt.datetime(test_year, test_month, 2, 0, 0, 2,
                                tzinfo=current_tz)
        mocked_timezone_now = MagicMock()
        mocked_timezone_now.return_value = test_date

        with patch('silver.models.timezone.now', mocked_timezone_now):
            subscription = SubscriptionFactory.create()

            subscription.start_date = dt.date(test_year, test_month, 1)
            subscription.plan.generate_after = 120
            subscription.plan.interval = 'day'
            subscription.plan.interval_count = 1
            subscription.save()

            assert subscription.should_be_billed == False

    def test_first_billing_one_day_interval_positive_generate_after_limit(self):
        test_year = 2015
        test_month = 2
        current_tz = timezone.get_current_timezone()
        test_date = dt.datetime(test_year, test_month, 2, 0, 2, 0,
                                tzinfo=current_tz)
        mocked_timezone_now = MagicMock()
        mocked_timezone_now.return_value = test_date

        with patch('silver.models.timezone.now', mocked_timezone_now):
            subscription = SubscriptionFactory.create()

            subscription.start_date = dt.date(test_year, test_month, 1)
            subscription.plan.generate_after = 120
            subscription.plan.interval = 'day'
            subscription.plan.interval_count = 1
            subscription.save()

            assert subscription.should_be_billed == False

    def test_first_billing_one_day_interval_positive_generate_after_pass(self):
        test_year = 2015
        test_month = 2
        current_tz = timezone.get_current_timezone()
        test_date = dt.datetime(test_year, test_month, 2, 0, 2, 1,
                                tzinfo=current_tz)
        mocked_timezone_now = MagicMock()
        mocked_timezone_now.return_value = test_date

        with patch('silver.models.timezone.now', mocked_timezone_now):
            subscription = SubscriptionFactory.create()

            subscription.start_date = dt.date(test_year, test_month, 1)
            subscription.plan.generate_after = 120
            subscription.plan.interval = 'day'
            subscription.plan.interval_count = 1
            subscription.save()

            assert subscription.should_be_billed == True

    def test_first_billing_one_day_interval_limit(self):
        test_year = 2015
        test_month = 2
        current_tz = timezone.get_current_timezone()
        test_date = dt.datetime(test_year, test_month, 2, 0, 0, 0,
                                tzinfo=current_tz)
        mocked_timezone_now = MagicMock()
        mocked_timezone_now.return_value = test_date

        with patch('silver.models.timezone.now', mocked_timezone_now):
            subscription = SubscriptionFactory.create()

            subscription.start_date = dt.date(test_year, test_month, 1)
            subscription.plan.generate_after = 0
            subscription.plan.interval = 'day'
            subscription.plan.interval_count = 1
            subscription.save()

            assert subscription.should_be_billed == False

    def test_first_billing_one_day_interval_below_limit(self):
        test_year = 2015
        test_month = 2
        current_tz = timezone.get_current_timezone()
        test_date = dt.datetime(test_year, test_month, 1, 0, 0, 0,
                                tzinfo=current_tz)
        mocked_timezone_now = MagicMock()
        mocked_timezone_now.return_value = test_date

        with patch('silver.models.timezone.now', mocked_timezone_now):
            subscription = SubscriptionFactory.create()

            subscription.start_date = dt.date(test_year, test_month, 1)
            subscription.plan.generate_after = 0
            subscription.plan.interval = 'day'
            subscription.plan.interval_count = 1
            subscription.save()

            assert subscription.should_be_billed == False

    def test_reissue_one_year_interval(self):
        test_year = 2015
        test_month = 3
        current_tz = timezone.get_current_timezone()
        test_date = dt.datetime(test_year, test_month, 1, tzinfo=current_tz)
        mocked_timezone_now = MagicMock()
        mocked_timezone_now.return_value = test_date

        with patch('silver.models.timezone.now', mocked_timezone_now):
            subscription = SubscriptionFactory.create()

            subscription.last_billing_date = dt.date(2014, 2, 1)
            subscription.plan.generate_after = 0
            subscription.plan.interval = 'year'
            subscription.plan.interval_count = 1
            subscription.save()

            assert subscription.should_be_billed == True

    def test_reissue_one_year_interval_limit(self):
        test_year = 2015
        test_month = 2
        current_tz = timezone.get_current_timezone()
        test_date = dt.datetime(test_year, test_month, 1, tzinfo=current_tz)
        mocked_timezone_now = MagicMock()
        mocked_timezone_now.return_value = test_date

        with patch('silver.models.timezone.now', mocked_timezone_now):
            subscription = SubscriptionFactory.create()

            subscription.last_billing_date = dt.date(2014, 2, 1)
            subscription.plan.generate_after = 0
            subscription.plan.interval = 'year'
            subscription.plan.interval_count = 1
            subscription.save()

            assert subscription.should_be_billed == False

    def test_reissue_one_year_interval_below_limit(self):
        test_year = 2015
        test_month = 1
        current_tz = timezone.get_current_timezone()
        test_date = dt.datetime(test_year, test_month, 1, tzinfo=current_tz)
        mocked_timezone_now = MagicMock()
        mocked_timezone_now.return_value = test_date

        with patch('silver.models.timezone.now', mocked_timezone_now):
            subscription = SubscriptionFactory.create()

            subscription.last_billing_date = dt.date(2014, 2, 1)
            subscription.plan.generate_after = 0
            subscription.plan.interval = 'year'
            subscription.plan.interval_count = 1
            subscription.save()

            assert subscription.should_be_billed == False

    def test_reissue_two_years_interval(self):
        test_year = 2015
        test_month = 3
        current_tz = timezone.get_current_timezone()
        test_date = dt.datetime(test_year, test_month, 1, tzinfo=current_tz)
        mocked_timezone_now = MagicMock()
        mocked_timezone_now.return_value = test_date

        with patch('silver.models.timezone.now', mocked_timezone_now):
            subscription = SubscriptionFactory.create()

            subscription.last_billing_date = dt.date(test_year - 2, 2, 1)
            subscription.plan.generate_after = 0
            subscription.plan.interval = 'year'
            subscription.plan.interval_count = 2
            subscription.save()

            assert subscription.should_be_billed == True

    def test_reissue_two_years_interval_limit(self):
        test_year = 2015
        test_month = 2
        current_tz = timezone.get_current_timezone()
        test_date = dt.datetime(test_year, test_month, 1, tzinfo=current_tz)
        mocked_timezone_now = MagicMock()
        mocked_timezone_now.return_value = test_date

        with patch('silver.models.timezone.now', mocked_timezone_now):
            subscription = SubscriptionFactory.create()

            subscription.last_billing_date = dt.date(test_year - 2, 2, 1)
            subscription.plan.generate_after = 0
            subscription.plan.interval = 'year'
            subscription.plan.interval_count = 2
            subscription.save()

            assert subscription.should_be_billed == False

    def test_reissue_two_years_interval_below_limit(self):
        test_year = 2015
        test_month = 1
        current_tz = timezone.get_current_timezone()
        test_date = dt.datetime(test_year, test_month, 1, tzinfo=current_tz)
        mocked_timezone_now = MagicMock()
        mocked_timezone_now.return_value = test_date

        with patch('silver.models.timezone.now', mocked_timezone_now):
            subscription = SubscriptionFactory.create()

            subscription.last_billing_date = dt.date(test_year - 2, 2, 1)
            subscription.plan.generate_after = 0
            subscription.plan.interval = 'year'
            subscription.plan.interval_count = 2
            subscription.save()

            assert subscription.should_be_billed == False

    def test_reissue_one_month_interval(self):
        test_year = 2015
        test_month = 3
        test_day = 20
        current_tz = timezone.get_current_timezone()
        test_date = dt.datetime(test_year, test_month, test_day,
                                tzinfo=current_tz)
        mocked_timezone_now = MagicMock()
        mocked_timezone_now.return_value = test_date

        with patch('silver.models.timezone.now', mocked_timezone_now):
            subscription = SubscriptionFactory.create()

            subscription.last_billing_date = dt.date(test_year, test_month - 1,
                                                     test_day - 1)
            subscription.plan.generate_after = 0
            subscription.plan.interval = 'month'
            subscription.plan.interval_count = 1
            subscription.save()

            assert subscription.should_be_billed == True

    def test_reissue_one_month_interval_limit(self):
        test_year = 2015
        test_month = 3
        test_day = 20
        current_tz = timezone.get_current_timezone()
        test_date = dt.datetime(test_year, test_month, test_day,
                                tzinfo=current_tz)
        mocked_timezone_now = MagicMock()
        mocked_timezone_now.return_value = test_date

        with patch('silver.models.timezone.now', mocked_timezone_now):
            subscription = SubscriptionFactory.create()

            subscription.last_billing_date = dt.date(test_year, test_month - 1,
                                                     test_day)
            subscription.plan.generate_after = 0
            subscription.plan.interval = 'month'
            subscription.plan.interval_count = 1
            subscription.save()

            assert subscription.should_be_billed == False

    def test_reissue_one_month_interval_below_limit(self):
        test_year = 2015
        test_month = 3
        test_day = 20
        current_tz = timezone.get_current_timezone()
        test_date = dt.datetime(test_year, test_month, test_day - 10,
                                tzinfo=current_tz)
        mocked_timezone_now = MagicMock()
        mocked_timezone_now.return_value = test_date

        with patch('silver.models.timezone.now', mocked_timezone_now):
            subscription = SubscriptionFactory.create()

            subscription.last_billing_date = dt.date(test_year, test_month - 1,
                                                     test_day)
            subscription.plan.generate_after = 0
            subscription.plan.interval = 'month'
            subscription.plan.interval_count = 1
            subscription.save()

            assert subscription.should_be_billed == False

    def test_reissue_two_months_interval(self):
        test_year = 2015
        test_month = 3
        test_day = 20
        current_tz = timezone.get_current_timezone()
        test_date = dt.datetime(test_year, test_month, test_day,
                                tzinfo=current_tz)
        mocked_timezone_now = MagicMock()
        mocked_timezone_now.return_value = test_date

        with patch('silver.models.timezone.now', mocked_timezone_now):
            subscription = SubscriptionFactory.create()

            subscription.last_billing_date = dt.date(test_year, test_month - 2,
                                                     test_day - 1)
            subscription.plan.generate_after = 0
            subscription.plan.interval = 'month'
            subscription.plan.interval_count = 2
            subscription.save()

            assert subscription.should_be_billed == True

    def test_reissue_two_months_interval_limit(self):
        test_year = 2015
        test_month = 3
        test_day = 20
        current_tz = timezone.get_current_timezone()
        test_date = dt.datetime(test_year, test_month, test_day,
                                tzinfo=current_tz)
        mocked_timezone_now = MagicMock()
        mocked_timezone_now.return_value = test_date

        with patch('silver.models.timezone.now', mocked_timezone_now):
            subscription = SubscriptionFactory.create()

            subscription.last_billing_date = dt.date(test_year, test_month - 2,
                                                     test_day)
            subscription.plan.generate_after = 0
            subscription.plan.interval = 'month'
            subscription.plan.interval_count = 2
            subscription.save()

            assert subscription.should_be_billed == False

    def test_reissue_two_months_interval_below_limit(self):
        test_year = 2015
        test_month = 3
        test_day = 20
        current_tz = timezone.get_current_timezone()
        test_date = dt.datetime(test_year, test_month, test_day - 1,
                                tzinfo=current_tz)
        mocked_timezone_now = MagicMock()
        mocked_timezone_now.return_value = test_date

        with patch('silver.models.timezone.now', mocked_timezone_now):
            subscription = SubscriptionFactory.create()

            subscription.last_billing_date = dt.date(test_year, test_month - 2,
                                                     test_day)
            subscription.plan.generate_after = 0
            subscription.plan.interval = 'month'
            subscription.plan.interval_count = 2
            subscription.save()

            assert subscription.should_be_billed == False

    def test_reissue_one_week_interval(self):
        last_issue_year = 2015
        last_issue_month = 3
        last_issue_day = 20
        delta = dt.timedelta(weeks=1, days=1)
        current_tz = timezone.get_current_timezone()
        test_date = dt.datetime(last_issue_year, last_issue_month,
                                last_issue_day, tzinfo=current_tz) + delta
        mocked_timezone_now = MagicMock()
        mocked_timezone_now.return_value = test_date

        with patch('silver.models.timezone.now', mocked_timezone_now):
            subscription = SubscriptionFactory.create()

            subscription.last_billing_date = dt.date(last_issue_year,
                                                     last_issue_month,
                                                     last_issue_day)
            subscription.plan.generate_after = 0
            subscription.plan.interval = 'week'
            subscription.plan.interval_count = 1
            subscription.save()

            assert subscription.should_be_billed == True

    def test_reissue_one_week_interval_limit(self):
        last_issue_year = 2015
        last_issue_month = 3
        last_issue_day = 20
        delta = dt.timedelta(weeks=1)
        current_tz = timezone.get_current_timezone()
        test_date = dt.datetime(last_issue_year, last_issue_month,
                                last_issue_day, tzinfo=current_tz) + delta
        mocked_timezone_now = MagicMock()
        mocked_timezone_now.return_value = test_date

        with patch('silver.models.timezone.now', mocked_timezone_now):
            subscription = SubscriptionFactory.create()

            subscription.last_billing_date = dt.date(last_issue_year,
                                                     last_issue_month,
                                                     last_issue_day)
            subscription.plan.generate_after = 0
            subscription.plan.interval = 'week'
            subscription.plan.interval_count = 1
            subscription.save()

            assert subscription.should_be_billed == False

    def test_reissue_one_week_interval_below_limit(self):
        last_issue_year = 2015
        last_issue_month = 3
        last_issue_day = 20
        delta = dt.timedelta(weeks=1, days=-1)
        current_tz = timezone.get_current_timezone()
        test_date = dt.datetime(last_issue_year, last_issue_month,
                                last_issue_day, tzinfo=current_tz) + delta
        mocked_timezone_now = MagicMock()
        mocked_timezone_now.return_value = test_date

        with patch('silver.models.timezone.now', mocked_timezone_now):
            subscription = SubscriptionFactory.create()

            subscription.last_billing_date = dt.date(last_issue_year,
                                                     last_issue_month,
                                                     last_issue_day)
            subscription.plan.generate_after = 0
            subscription.plan.interval = 'week'
            subscription.plan.interval_count = 1
            subscription.save()

            assert subscription.should_be_billed == False
