import datetime as dt
from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase
#from django.utils.six import StringIO
from django.utils import timezone
from mock import MagicMock, patch, PropertyMock

from silver.models import Proforma, DocumentEntry, Invoice
from silver.tests.factories import (SubscriptionFactory, PlanFactory,
                                    MeteredFeatureFactory)
from silver.utils import get_object_or_None

class TestInvoiceGenerationCommand(TestCase):

    def test_on_trial_subscription_without_metered_features_to_draft(self):
        now = dt.datetime(2015, 2, 7, tzinfo=timezone.get_current_timezone())

        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  trial_period_days=7, amount=Decimal('200.00'))
        start_date = now.date() + dt.timedelta(days=-9)  # should be 2015-01-29
        trial_end = start_date + dt.timedelta(days=plan.trial_period_days)

        subscription = SubscriptionFactory.create(
            plan=plan, start_date=start_date, trial_end=trial_end)
        subscription.activate()
        subscription.save()

        mocked_is_on_trial = PropertyMock(return_value=True)
        mocked_should_be_billed = PropertyMock(return_value=True)
        with patch.multiple('silver.models.Subscription',
                            is_on_trial=mocked_is_on_trial,
                            should_be_billed=mocked_should_be_billed):
            mocked_timezone_now = MagicMock()
            mocked_timezone_now.return_value.date.return_value = dt.date(2015, 2, 9)
            with patch('silver.management.commands.generate_billing_documents.timezone.now',
                    mocked_timezone_now):
                call_command('generate_billing_documents')

                # Expect one Proforma
                assert Proforma.objects.all().count() == 1
                assert Invoice.objects.all().count() == 0

                # In draft state
                assert Proforma.objects.get(id=1).state == 'draft'

                # The only entry will be the plan
                assert DocumentEntry.objects.all().count() == 1
                doc = get_object_or_None(DocumentEntry, id=1)

                # With price 0, as it is in trial period
                assert doc.unit_price == Decimal('0.00')

                # And quantity 1
                assert doc.quantity == 1

    def test_on_trial_subscription_without_metered_features_to_issued(self):
        now = dt.datetime(2015, 2, 7, tzinfo=timezone.get_current_timezone())

        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  trial_period_days=7, amount=Decimal('200.00'))
        plan.provider.default_document_state = 'issued'
        plan.provider.save()

        start_date = now.date() + dt.timedelta(days=-9)  # should be 2015-01-29
        trial_end = start_date + dt.timedelta(days=plan.trial_period_days)

        subscription = SubscriptionFactory.create(
            plan=plan, start_date=start_date, trial_end=trial_end)
        subscription.activate()
        subscription.save()

        mocked_is_on_trial = PropertyMock(return_value=True)
        mocked_should_be_billed = PropertyMock(return_value=True)
        with patch.multiple('silver.models.Subscription',
                            is_on_trial=mocked_is_on_trial,
                            should_be_billed=mocked_should_be_billed):
            mocked_timezone_now = MagicMock()
            mocked_timezone_now.return_value.date.return_value = dt.date(2015, 2, 9)
            with patch('silver.management.commands.generate_billing_documents.timezone.now',
                    mocked_timezone_now):
                call_command('generate_billing_documents')

                # Expect only one Proforma
                assert Proforma.objects.all().count() == 1
                assert Invoice.objects.all().count() == 0

                # In draft state
                assert Proforma.objects.get(id=1).state == 'issued'

                # The only entry will be the plan
                assert DocumentEntry.objects.all().count() == 1
                doc = get_object_or_None(DocumentEntry, id=1)

                # With price 0, as it is in trial period
                assert doc.unit_price == Decimal('0.00')

                # And quantity 1
                assert doc.quantity == 1

    def test_on_trial_subscription_with_metered_features_to_draft(self):
        now = dt.datetime(2015, 2, 7, tzinfo=timezone.get_current_timezone())

        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  trial_period_days=7, amount=Decimal('200.00'))
        start_date = now.date() + dt.timedelta(days=-9)  # should be 2015-01-29
        trial_end = start_date + dt.timedelta(days=plan.trial_period_days)

        subscription = SubscriptionFactory.create(
            plan=plan, start_date=start_date, trial_end=trial_end)
        subscription.activate()
        subscription.save()

        mocked_is_on_trial = PropertyMock(return_value=True)
        mocked_should_be_billed = PropertyMock(return_value=True)
        with patch.multiple('silver.models.Subscription',
                            is_on_trial=mocked_is_on_trial,
                            should_be_billed=mocked_should_be_billed):
            mocked_timezone_now = MagicMock()
            mocked_timezone_now.return_value.date.return_value = dt.date(2015, 2, 9)
            with patch('silver.management.commands.generate_billing_documents.timezone.now',
                    mocked_timezone_now):
                call_command('generate_billing_documents')

                # Expect one Proforma
                assert Proforma.objects.all().count() == 1
                assert Invoice.objects.all().count() == 0

                # In draft state
                assert Proforma.objects.get(id=1).state == 'draft'

                # The only entry will be the plan
                assert DocumentEntry.objects.all().count() == 1
                doc = get_object_or_None(DocumentEntry, id=1)

                # With price 0, as it is in trial period
                assert doc.unit_price == Decimal('0.00')

                # And quantity 1
                assert doc.quantity == 1
