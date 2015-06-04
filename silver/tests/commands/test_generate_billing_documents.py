import datetime as dt
from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase
# from django.utils.six import StringIO
from django.utils import timezone
from mock import patch, PropertyMock, MagicMock

from silver.models import (Proforma, DocumentEntry, Invoice, Subscription,
    Customer)
from silver.tests.factories import (SubscriptionFactory, PlanFactory,
                                    MeteredFeatureFactory,
                                    MeteredFeatureUnitsLogFactory,
                                    CustomerFactory)
from silver.utils import get_object_or_None


class TestInvoiceGenerationCommand(TestCase):
    def test_canceled_subscription_with_trial_with_metered_features_to_draft(self):
        billing_date = '2015-03-01'

        metered_feature = MeteredFeatureFactory(included_units=Decimal('0.00'))
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  trial_period_days=7, amount=Decimal('200.00'),
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 02, 01)
        trial_end = start_date + dt.timedelta(days=plan.trial_period_days)

        subscription = SubscriptionFactory.create(
            plan=plan, start_date=start_date, trial_end=trial_end)
        subscription.activate()
        subscription.cancel()
        subscription.save()

        mf_units_log_during_trial = MeteredFeatureUnitsLogFactory(
            subscription=subscription, metered_feature=metered_feature,
            start_date=start_date, end_date=trial_end
        )

        mf_units_log_after_trial = MeteredFeatureUnitsLogFactory(
            subscription=subscription, metered_feature=metered_feature,
            start_date=trial_end + dt.timedelta(days=1),
            # canceled 4 days before the end of the month
            end_date=dt.datetime(2015, 2, 24)
        )

        mocked_on_trial = MagicMock(return_value=False)
        with patch.multiple('silver.models.Subscription',
                            on_trial=mocked_on_trial):
            call_command('generate_docs', billing_date=billing_date)

            # Expect one Proforma
            assert Proforma.objects.all().count() == 1
            assert Invoice.objects.all().count() == 0

            # In draft state
            assert Proforma.objects.get(id=1).state == 'draft'

            # Expect 6 entries:
            # Plan Trial (+-), Plan Trial Metered Feature (+-),
            # Plan After Trial (+),  Metered Features After Trial (+)
            for doc in DocumentEntry.objects.all():
                print doc
            assert DocumentEntry.objects.all().count() == 6

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

    def test_canceled_subscription_with_metered_features_to_draft(self):
        billing_date = '2015-03-01'

        metered_feature = MeteredFeatureFactory(included_units=Decimal('0.00'))
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  trial_period_days=7, amount=Decimal('200.00'),
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 1, 1)
        trial_end = start_date + dt.timedelta(days=plan.trial_period_days)

        subscription = SubscriptionFactory.create(
            plan=plan, start_date=start_date, trial_end=trial_end)
        subscription.activate()
        subscription.cancel()
        subscription.save()

        mf_units_log = MeteredFeatureUnitsLogFactory(
            subscription=subscription, metered_feature=metered_feature,
            start_date=dt.datetime(2015, 2, 1),
            end_date=dt.datetime(2015, 2, 24)
        )

        mocked_is_on_trial = PropertyMock(return_value=False)
        mocked_last_billing_date = PropertyMock(
            return_value=dt.date(2015, 2, 1)
        )
        mocked_is_billed_first_time = PropertyMock(return_value=False)
        with patch.multiple('silver.models.Subscription',
                            is_on_trial=mocked_is_on_trial,
                            last_billing_date=mocked_last_billing_date,
                            is_billed_first_time=mocked_is_billed_first_time):
            call_command('generate_docs', billing_date=billing_date)

            # Expect one Proforma
            assert Proforma.objects.all().count() == 1
            assert Invoice.objects.all().count() == 0

            # Expect 1 entry:
            # Extra Metered Features (+)
            assert DocumentEntry.objects.all().count() == 1

            doc = get_object_or_None(DocumentEntry, id=1)
            assert doc.unit_price == metered_feature.price_per_unit
            assert doc.quantity == mf_units_log.consumed_units

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

    def test_gen_for_non_consolidated_billing(self):
        billing_date = '2015-02-09'

        customer = CustomerFactory.create(consolidated_billing=False)

        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  trial_period_days=7, amount=Decimal('200.00'))
        start_date = dt.date(2015, 1, 3)

        SubscriptionFactory.create_batch(
            3, plan=plan, start_date=start_date, customer=customer)

        for subscription in Subscription.objects.all():
            subscription.activate()
            subscription.save()

        mocked_on_trial = MagicMock(return_value=False)
        with patch.multiple('silver.models.Subscription',
                            on_trial=mocked_on_trial):
            call_command('generate_docs', billing_date=billing_date)

            assert Proforma.objects.all().count() == 3
            assert Invoice.objects.all().count() == 0

    def test_gen_for_single_canceled_subscription(self):
        billing_date = '2015-04-03'

        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  trial_period_days=7, amount=Decimal('200.00'))
        start_date = dt.date(2014, 1, 3)
        trial_end = start_date + dt.timedelta(days=plan.trial_period_days)

        subscription = SubscriptionFactory.create(
            plan=plan, start_date=start_date, trial_end=trial_end)
        subscription.activate()
        subscription.cancel()
        subscription.save()

        mocked_on_trial = MagicMock(return_value=True)
        with patch.multiple('silver.models.Subscription',
                            on_trial=mocked_on_trial):
            call_command(
                'generate_docs', subscription='1', billing_date=billing_date
            )

            assert Subscription.objects.filter(state='ended').count() == 1

            assert Proforma.objects.all().count() == 1
            assert Invoice.objects.all().count() == 0

    def test_gen_active_and_canceled_selection(self):
        billing_date = '2015-02-09'

        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  trial_period_days=7, amount=Decimal('200.00'))
        start_date = dt.date(2015, 1, 29)
        trial_end = start_date + dt.timedelta(days=plan.trial_period_days)

        SubscriptionFactory.create_batch(
            5, plan=plan, start_date=start_date, trial_end=trial_end)
        for subscription in Subscription.objects.all():
            subscription.activate()
            subscription.save()
        for subscription in Subscription.objects.filter(id__gte=2, id__lte=4):
            subscription.cancel()
            subscription.save()

        mocked_on_trial = MagicMock(return_value=True)
        with patch.multiple('silver.models.Subscription',
                            on_trial=mocked_on_trial):
            call_command('generate_docs', billing_date=billing_date)

            # Expect 5 Proformas (2 active Subs, 3 canceled)
            assert Proforma.objects.all().count() == 5
            assert Invoice.objects.all().count() == 0

            assert Subscription.objects.filter(state='ended').count() == 3

            Proforma.objects.all().delete()

            call_command('generate_docs', billing_date=billing_date)

            # Expect 2 Proformas (2 active Subs, 3 ended)
            assert Proforma.objects.all().count() == 2

    def test_subscription_with_trial_without_metered_features_to_draft(self):
        billing_date = '2015-03-02'

        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  trial_period_days=7, amount=Decimal('200.00'))

        start_date = dt.date(2015, 1, 29)
        trial_end = start_date + dt.timedelta(days=plan.trial_period_days)

        subscription = SubscriptionFactory.create(
            plan=plan, start_date=start_date, trial_end=trial_end)
        subscription.activate()
        subscription.save()

        print "subscription start-date", subscription.start_date

        Customer.objects.get(id=1).sales_tax_percent = Decimal('0.00')

        mocked_on_trial = MagicMock(return_value=False)
        with patch.multiple('silver.models.Subscription',
                            on_trial=mocked_on_trial):
            call_command('generate_docs', billing_date=billing_date)

            # Expect one Proforma
            assert Proforma.objects.all().count() == 1
            assert Invoice.objects.all().count() == 0

            # In draft state
            assert Proforma.objects.get(id=1).state == 'draft'

            # Expect 4 entries:
            # Plan Trial (+-), Plan Prorated (+), Plan for next month(+)
            assert DocumentEntry.objects.all().count() == 4

            doc = get_object_or_None(DocumentEntry, id=1)
            assert doc.unit_price == Decimal('69.35')  # (3 / 31 + 7 / 28) * 200

            doc = get_object_or_None(DocumentEntry, id=2)
            assert doc.unit_price == Decimal('-69.35')

            doc = get_object_or_None(DocumentEntry, id=3)
            assert doc.unit_price == Decimal('150.0000') # 21 / 28 * 200

            doc = get_object_or_None(DocumentEntry, id=4)
            assert doc.unit_price == Decimal('200.0000') # 21 / 28 * 200

            # And quantity 1
            assert doc.quantity == 1

    def test_subscription_with_trial_with_metered_features_to_draft(self):
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

        mocked_on_trial = MagicMock(return_value=False)
        with patch.multiple('silver.models.Subscription',
                            on_trial=mocked_on_trial):
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
