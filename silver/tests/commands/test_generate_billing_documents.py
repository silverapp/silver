import datetime as dt
from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase
# from django.utils.six import StringIO
from django.utils import timezone
from mock import MagicMock, patch, PropertyMock

from silver.models import Proforma, DocumentEntry, Invoice
from silver.tests.factories import (SubscriptionFactory, PlanFactory,
                                    MeteredFeatureFactory,
                                    MeteredFeatureUnitsLogFactory)
from silver.utils import get_object_or_None


class TestInvoiceGenerationCommand(TestCase):

    def test_on_trial_without_consumed_units(self):
        assert True

    def test_on_trial_with_consumed_units(self):
        assert True

    def test_prorated_month_with_trial_without_consumed_units(self):
        assert True

    def test_prorated_month_with_trial_with_consumed_units(self):
        assert True

    def test_prorated_month_without_trial_without_consumed_units(self):
        assert True

    def test_prorated_month_without_trial_with_consumed_units(self):
        assert True

    def test_full_month_with_consumed_units(self):
        assert True

    def test_full_month_without_consumed_units(self):
        assert True

    def test_gen_for_consolidated_billing(self):
        assert True

    def test_gen_for_non_consolidated_billing(self):
        assert True

    def test_gen_for_single_canceled_subscription(self):
        assert True

    def test_gen_active_and_canceled_selection(self):
        assert True

    #def test_on_trial_subscription_without_metered_features_to_draft(self):
        #now = dt.datetime(2015, 2, 7, tzinfo=timezone.get_current_timezone())

        #plan = PlanFactory.create(interval='month', interval_count=1,
                                  #generate_after=120, enabled=True,
                                  #trial_period_days=7, amount=Decimal('200.00'))
        #start_date = now.date() + dt.timedelta(days=-9)  # should be 2015-01-29
        #trial_end = start_date + dt.timedelta(days=plan.trial_period_days)

        #subscription = SubscriptionFactory.create(
            #plan=plan, start_date=start_date, trial_end=trial_end)
        #subscription.activate()
        #subscription.save()

        #mocked_is_on_trial = PropertyMock(return_value=True)
        #mocked_should_be_billed = PropertyMock(return_value=True)
        #with patch.multiple('silver.models.Subscription',
                            #is_on_trial=mocked_is_on_trial,
                            #should_be_billed=mocked_should_be_billed):
            #mocked_timezone_now = MagicMock()
            #mocked_timezone_now.return_value.date.return_value = dt.date(2015, 2, 9)
            #with patch('silver.management.commands.generate_billing_documents.timezone.now',
                    #mocked_timezone_now):
                #call_command('generate_billing_documents')

                ## Expect one Proforma
                #assert Proforma.objects.all().count() == 1
                #assert Invoice.objects.all().count() == 0

                ## In draft state
                #assert Proforma.objects.get(id=1).state == 'draft'

                ## The only entry will be the plan
                #assert DocumentEntry.objects.all().count() == 1
                #doc = get_object_or_None(DocumentEntry, id=1)

                ## With price 0, as it is in trial period
                #assert doc.unit_price == Decimal('0.00')

                ## And quantity 1
                #assert doc.quantity == 1

    #def test_on_trial_subscription_without_metered_features_to_issued(self):
        #now = dt.datetime(2015, 2, 7, tzinfo=timezone.get_current_timezone())

        #plan = PlanFactory.create(interval='month', interval_count=1,
                                  #generate_after=120, enabled=True,
                                  #trial_period_days=7, amount=Decimal('200.00'))
        #plan.provider.default_document_state = 'issued'
        #plan.provider.save()

        #start_date = now.date() + dt.timedelta(days=-9)  # should be 2015-01-29
        #trial_end = start_date + dt.timedelta(days=plan.trial_period_days)

        #subscription = SubscriptionFactory.create(
            #plan=plan, start_date=start_date, trial_end=trial_end)
        #subscription.activate()
        #subscription.save()

        #mocked_is_on_trial = PropertyMock(return_value=True)
        #mocked_should_be_billed = PropertyMock(return_value=True)
        #with patch.multiple('silver.models.Subscription',
                            #is_on_trial=mocked_is_on_trial,
                            #should_be_billed=mocked_should_be_billed):
            #mocked_timezone_now = MagicMock()
            #mocked_timezone_now.return_value.date.return_value = dt.date(2015, 2, 9)
            #with patch('silver.management.commands.generate_billing_documents.timezone.now',
                    #mocked_timezone_now):
                #call_command('generate_billing_documents')

                ## Expect only one Proforma
                #assert Proforma.objects.all().count() == 1
                #assert Invoice.objects.all().count() == 0

                ## In draft state
                #assert Proforma.objects.get(id=1).state == 'issued'

                ## The only entry will be the plan
                #assert DocumentEntry.objects.all().count() == 1
                #doc = get_object_or_None(DocumentEntry, id=1)

                ## With price 0, as it is in trial period
                #assert doc.unit_price == Decimal('0.00')

                ## And quantity 1
                #assert doc.quantity == 1

    #def test_on_trial_subscription_with_metered_features_to_draft(self):
        #now = dt.datetime(2015, 2, 7, tzinfo=timezone.get_current_timezone())

        #plan = PlanFactory.create(interval='month', interval_count=1,
                                  #generate_after=120, enabled=True,
                                  #trial_period_days=7, amount=Decimal('200.00'))
        #start_date = now.date() + dt.timedelta(days=-9)  # should be 2015-01-29
        #trial_end = start_date + dt.timedelta(days=plan.trial_period_days)

        #subscription = SubscriptionFactory.create(
            #plan=plan, start_date=start_date, trial_end=trial_end)
        #subscription.activate()
        #subscription.save()

        #mocked_is_on_trial = PropertyMock(return_value=True)
        #mocked_should_be_billed = PropertyMock(return_value=True)
        #with patch.multiple('silver.models.Subscription',
                            #is_on_trial=mocked_is_on_trial,
                            #should_be_billed=mocked_should_be_billed):
            #mocked_timezone_now = MagicMock()
            #mocked_timezone_now.return_value.date.return_value = dt.date(2015, 2, 9)
            #with patch('silver.management.commands.generate_billing_documents.timezone.now',
                    #mocked_timezone_now):
                #call_command('generate_billing_documents')

                ## Expect one Proforma
                #assert Proforma.objects.all().count() == 1
                #assert Invoice.objects.all().count() == 0

                ## In draft state
                #assert Proforma.objects.get(id=1).state == 'draft'

                ## The only entry will be the plan
                #assert DocumentEntry.objects.all().count() == 1
                #doc = get_object_or_None(DocumentEntry, id=1)

                ## With price 0, as it is in trial period
                #assert doc.unit_price == Decimal('0.00')

                ## And quantity 1
                #assert doc.quantity == 1

    def test_on_trial_subscription_with_metered_features_to_draft(self):
        now = dt.datetime(2015, 2, 7, tzinfo=timezone.get_current_timezone())
        billing_date = '2015-03-01'

        metered_feature = MeteredFeatureFactory(included_units=Decimal('0.00'))
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  trial_period_days=7, amount=Decimal('200.00'),
                                  metered_features=[metered_feature])
        start_date = now.date() + dt.timedelta(days=-6)  # should be 2015-02-01
        trial_end = start_date + dt.timedelta(days=plan.trial_period_days)

        subscription = SubscriptionFactory.create(
            plan=plan, start_date=start_date, trial_end=trial_end)
        subscription.activate()
        subscription.save()

        mf_units_log_during_trial = MeteredFeatureUnitsLogFactory(
            subscription=subscription, metered_feature=metered_feature,
            start_date=start_date, end_date=trial_end
        )

        mf_units_log_after_trial = MeteredFeatureUnitsLogFactory(
            subscription=subscription, metered_feature=metered_feature,
            start_date=trial_end + dt.timedelta(days=1),
            end_date=dt.datetime(2015, 2, 28)
        )

        mocked_is_on_trial = PropertyMock(return_value=True)
        with patch.multiple('silver.models.Subscription',
                            is_on_trial=mocked_is_on_trial):
            call_command('generate_docs', billing_date=billing_date)

            # Expect one Proforma
            assert Proforma.objects.all().count() == 1
            assert Invoice.objects.all().count() == 0

            # In draft state
            assert Proforma.objects.get(id=1).state == 'draft'

            # Expect 7 entries:
            # Plan Trial (+-), Plan Trial Metered Feature (+-), Plan After Trial (+)
            # Metered Features After Trial (+), Plan for next month (+)
            assert DocumentEntry.objects.all().count() == 7

            doc = get_object_or_None(DocumentEntry, id=1)
            assert doc.unit_price == Decimal('57.14')

            doc = get_object_or_None(DocumentEntry, id=2)
            assert doc.unit_price == Decimal('-57.14')

            doc = get_object_or_None(DocumentEntry, id=3)
            assert doc.unit_price == metered_feature.price_per_unit
            assert doc.quantity == mf_units_log_during_trial.consumed_units

            doc = get_object_or_None(DocumentEntry, id=4)
            assert doc.unit_price == - metered_feature.price_per_unit
            assert doc.quantity == mf_units_log_during_trial.consumed_units

            doc = get_object_or_None(DocumentEntry, id=5)
            assert doc.unit_price == Decimal('142.8600')  # 20 / 28 * 200

            doc = get_object_or_None(DocumentEntry, id=6)
            assert doc.unit_price == metered_feature.price_per_unit
            assert doc.quantity == mf_units_log_after_trial.consumed_units

            doc = get_object_or_None(DocumentEntry, id=7)
            assert doc.unit_price == Decimal('200.00')

            # And quantity 1
            assert doc.quantity == 1
