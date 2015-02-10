import datetime as dt

from django.core.management import call_command
from django.test import TestCase
from django.utils.six import StringIO
from django.utils import timezone
from mock import MagicMock, patch, PropertyMock

from silver.models import Proforma
from silver.tests.factories import (SubscriptionFactory, PlanFactory)

class TestInvoiceGenerationCommand(TestCase):

    def test_on_trial_subscription(self):
        now = dt.datetime(2015, 2, 7, tzinfo=timezone.get_current_timezone())
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  trial_period_days=7)
        start_date = now + dt.timedelta(days=-9)  # should be 2015-01-29
        trial_end = start_date + dt.timedelta(days=plan.trial_period_days)
        SubscriptionFactory.create(plan=plan, start_date=start_date,
                                   trial_end=trial_end)

        mocked_is_on_trial = PropertyMock(return_value=True)
        mocked_should_be_billed = PropertyMock(return_value=True)
        with patch.multiple('silver.models.Subscription',
                            is_on_trial=mocked_is_on_trial,
                            should_be_billed=mocked_should_be_billed):
            mocked_timezone_now = MagicMock()
            mocked_timezone_now.return_value.date.return_value = dt.date(2015, 2, 9)
            with patch('silver.management.commands.generate_billing_documents.timezone.now',
                    mocked_timezone_now):
                out = StringIO()
                call_command('generate_billing_documents', stdout=out)

                assert Proforma.objects.all().count() == 1
