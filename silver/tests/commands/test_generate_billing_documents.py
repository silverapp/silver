import datetime as dt
from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase
from django.utils.six import StringIO
from django.utils import timezone
from mock import patch, PropertyMock, MagicMock

from silver.models import (Proforma, DocumentEntry, Invoice, Subscription,
                           Customer, MeteredFeatureUnitsLog)
from silver.tests.factories import (SubscriptionFactory, PlanFactory,
                                    MeteredFeatureFactory,
                                    MeteredFeatureUnitsLogFactory,
                                    CustomerFactory)
from silver.utils import get_object_or_None


class TestInvoiceGenerationCommand(TestCase):
    """
    Tests:
        * non-canceled
            * consolidated billing w/ included units --
            * consolidated billing w/a included units
            * consolidated billing w/ prorated subscriptions
            * consolidated -> subscriptions full as well as full trial
            * non-consolidated billing w/ included units --
            * non-consolidated billing w/a included units
            * non-consolidated billing w/ prorated subscriptions
            * Generate with different default states
                * draft --
                * issued
            * trial over multiple months
            * variations for non-canceled subscriptions. Check the cases paper
        * canceled
            * canceled subscription w/ trial --
            * canceled subscription w/a trial
            * canceled subscription w trial underflow --
            * canceled subscription w trial overflow --
    """

    def __init__(self, *args, **kwargs):
        super(TestInvoiceGenerationCommand, self).__init__(*args, **kwargs)
        self.output = StringIO()

    ###########################################################################
    # Non-Canceled
    ###########################################################################
    def test_gen_for_non_consolidated_billing(self, billing_date=None):
        """
        A customer  has 3 subscriptions for which we use the normal case:
            * add consumed mfs for the previous month
            * add the value of the plan for the next month
            => 3 different proformas
        """
        billing_date = billing_date or '2015-03-01'

        customer = CustomerFactory.create(consolidated_billing=False)

        plan_price = Decimal('200.00')
        metered_feature = MeteredFeatureFactory(included_units=Decimal('0.00'))
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  amount=plan_price,
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 1, 3)

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

        mocked_on_trial = MagicMock(return_value=False)
        mocked_last_billing_date = PropertyMock(
            return_value=dt.date(2015, 2, 1))
        mocked_is_billed_first_time = PropertyMock(return_value=False)
        with patch.multiple('silver.models.Subscription',
                            on_trial=mocked_on_trial,
                            last_billing_date=mocked_last_billing_date,
                            is_billed_first_time=mocked_is_billed_first_time):
            call_command('generate_docs', billing_date=billing_date,
                         stdout=self.output)

            assert Proforma.objects.all().count() == 3
            assert Invoice.objects.all().count() == 0

            assert DocumentEntry.objects.all().count() == 6

            for proforma in Proforma.objects.all():
                entries = proforma.proforma_entries.all()
                if 'plan' in entries[0].description.lower():
                    plan = entries[0]
                    units = entries[1]
                else:
                    units = entries[0]
                    plan = entries[1]

                assert plan.quantity == 1
                assert plan.unit_price == plan_price
                assert units.quantity == consumed_mfs
                assert units.unit_price == metered_feature.price_per_unit

    def test_gen_consolidated_billing(self, billing_date=None):
        """
        A customer  has 3 subscriptions for which we use the normal case:
            * add consumed mfs for the previous month for each subscription
            * add the value of the plan for the next month for each subscription
            => 1 proforma with all the aforementioned data
        """

        billing_date = billing_date or '2015-03-01'
        subscriptions_cnt = 3
        plan_price = Decimal('200.00')
        mf_price = Decimal('2.5')

        customer = CustomerFactory.create(
            consolidated_billing=True,
            sales_tax_percent=Decimal('0.00'))
        metered_feature = MeteredFeatureFactory(
            included_units=Decimal('0.00'), price_per_unit=mf_price)
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  amount=plan_price,
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 1, 3)

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

        mocked_on_trial = MagicMock(return_value=False)
        mocked_last_billing_date = PropertyMock(
            return_value=dt.date(2015, 2, 1))
        mocked_is_billed_first_time = PropertyMock(return_value=False)
        with patch.multiple('silver.models.Subscription',
                            on_trial=mocked_on_trial,
                            last_billing_date=mocked_last_billing_date,
                            is_billed_first_time=mocked_is_billed_first_time):
            call_command('generate_docs', billing_date=billing_date,
                         stdout=self.output)

            assert Proforma.objects.all().count() == 1
            assert Invoice.objects.all().count() == 0

            proforma = Proforma.objects.get(id=1)
            # For each doc, expect 2 entries: the plan value and the mfs
            assert proforma.proforma_entries.all().count() == subscriptions_cnt * 2

            expected_total = (subscriptions_cnt * plan_price +
                              subscriptions_cnt * (mf_price * consumed_mfs))
            assert proforma.total == expected_total

    def test_gen_consolidated_billing_without_mfs(self):
        """
        A customer  has 3 subscriptions for which it does not have any
        consumed metered features.
        """

        billing_date = '2015-03-01'
        subscriptions_cnt = 3
        plan_price = Decimal('200.00')
        mf_price = Decimal('2.5')

        customer = CustomerFactory.create(
            consolidated_billing=True,
            sales_tax_percent=Decimal('0.00'))
        metered_feature = MeteredFeatureFactory(
            included_units=Decimal('0.00'), price_per_unit=mf_price)
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  amount=plan_price,
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 1, 3)

        subscriptions = SubscriptionFactory.create_batch(
            size=subscriptions_cnt, plan=plan, start_date=start_date,
            customer=customer)

        for subscription in subscriptions:
            subscription.activate()
            subscription.save()

        mocked_on_trial = MagicMock(return_value=False)
        mocked_last_billing_date = PropertyMock(
            return_value=dt.date(2015, 2, 1))
        mocked_is_billed_first_time = PropertyMock(return_value=False)
        with patch.multiple('silver.models.Subscription',
                            on_trial=mocked_on_trial,
                            last_billing_date=mocked_last_billing_date,
                            is_billed_first_time=mocked_is_billed_first_time):
            call_command('generate_docs', billing_date=billing_date,
                         stdout=self.output)

            assert Proforma.objects.all().count() == 1
            assert Invoice.objects.all().count() == 0

            proforma = Proforma.objects.get(id=1)
            # For each doc, expect 1 entry: the plan value
            assert proforma.proforma_entries.all().count() == subscriptions_cnt

            expected_total = subscriptions_cnt * plan_price
            assert proforma.total == expected_total

    def test_subscription_with_trial_without_metered_features_to_draft(self):
        billing_date = '2015-03-02'

        plan_price = Decimal('200.00')
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  trial_period_days=15, amount=plan_price)

        start_date = dt.date(2015, 2, 4)
        trial_end = start_date + dt.timedelta(days=plan.trial_period_days - 1)

        subscription = SubscriptionFactory.create(
            plan=plan, start_date=start_date, trial_end=trial_end)
        subscription.activate()
        subscription.save()

        Customer.objects.get(id=1).sales_tax_percent = Decimal('0.00')

        mocked_on_trial = MagicMock(return_value=False)
        with patch.multiple('silver.models.Subscription',
                            on_trial=mocked_on_trial):
            call_command('generate_docs', billing_date=billing_date,
                         stdout=self.output)

            # Expect one Proforma
            assert Proforma.objects.all().count() == 1
            assert Invoice.objects.all().count() == 0

            # In draft state
            assert Proforma.objects.get(id=1).state == 'draft'

            # Expect 4 entries:
            # Plan Trial (+-), Plan Prorated (+), Plan for next month(+)
            assert DocumentEntry.objects.all().count() == 4

            doc = get_object_or_None(DocumentEntry, id=1)
            assert doc.unit_price == Decimal('107.1400')  # (15 / 28) * 200

            doc = get_object_or_None(DocumentEntry, id=2)
            assert doc.unit_price == Decimal('-107.1400')

            doc = get_object_or_None(DocumentEntry, id=3)
            assert doc.unit_price == Decimal('71.4200') # (10 / 28) * 200

            doc = get_object_or_None(DocumentEntry, id=4)
            assert doc.unit_price == plan_price

            # And quantity 1
            assert doc.quantity == 1

    def test_subscription_with_trial_with_metered_features_underflow_to_draft(self):
        billing_date = '2015-03-01'

        included_units_during_trial = Decimal('5.00')
        metered_feature = MeteredFeatureFactory(
            included_units=Decimal('0.00'),
            included_units_during_trial=included_units_during_trial)
        plan_price = Decimal('200.00')
        plan = PlanFactory.create(interval='month', interval_count=1,
                                  generate_after=120, enabled=True,
                                  trial_period_days=7, amount=plan_price,
                                  metered_features=[metered_feature])
        start_date = dt.date(2015, 2, 1)
        trial_end = start_date + dt.timedelta(days=plan.trial_period_days)

        subscription = SubscriptionFactory.create(
            plan=plan, start_date=start_date, trial_end=trial_end)
        subscription.activate()
        subscription.save()

        consumed_mfs_during_trial = Decimal('3.00')
        mf_units_log_during_trial = MeteredFeatureUnitsLogFactory(
            subscription=subscription, metered_feature=metered_feature,
            start_date=start_date, end_date=trial_end,
            consumed_units=consumed_mfs_during_trial)

        mf_units_log_after_trial = MeteredFeatureUnitsLogFactory(
            subscription=subscription, metered_feature=metered_feature,
            start_date=trial_end + dt.timedelta(days=1),
            end_date=dt.datetime(2015, 2, 28)
        )

        mocked_on_trial = MagicMock(return_value=False)
        with patch.multiple('silver.models.Subscription',
                            on_trial=mocked_on_trial):
            call_command('generate_docs', billing_date=billing_date,
                         stdout=self.output)

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
            assert doc.quantity == consumed_mfs_during_trial

            doc = get_object_or_None(DocumentEntry, id=4)
            assert doc.unit_price == - metered_feature.price_per_unit
            assert doc.quantity == consumed_mfs_during_trial

            doc = get_object_or_None(DocumentEntry, id=5)
            assert doc.unit_price == Decimal('142.8600')  # 20 / 28 * 200

            doc = get_object_or_None(DocumentEntry, id=6)
            assert doc.unit_price == metered_feature.price_per_unit
            assert doc.quantity == mf_units_log_after_trial.consumed_units

            doc = get_object_or_None(DocumentEntry, id=7)
            assert doc.unit_price == plan_price

            # And quantity 1
            assert doc.quantity == 1

    def test_subscription_with_trial_with_metered_features_overflow_to_draft(self):
        billing_date = '2015-03-01'

        units_included_during_trial = Decimal('5.00')
        metered_feature = MeteredFeatureFactory(
            included_units=Decimal('0.00'),
            included_units_during_trial=units_included_during_trial)
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
        mf_units_log_during_trial = MeteredFeatureUnitsLogFactory(
            subscription=subscription, metered_feature=metered_feature,
            start_date=start_date, end_date=trial_end,
            consumed_units=units_consumed_during_trial
        )

        mf_units_log_after_trial = MeteredFeatureUnitsLogFactory(
            subscription=subscription, metered_feature=metered_feature,
            start_date=trial_end + dt.timedelta(days=1),
            end_date=dt.datetime(2015, 2, 28)
        )

        mocked_on_trial = MagicMock(return_value=False)
        with patch.multiple('silver.models.Subscription',
                            on_trial=mocked_on_trial):
            call_command('generate_docs', billing_date=billing_date,
                         stdout=self.output)

            # Expect one Proforma
            assert Proforma.objects.all().count() == 1
            assert Invoice.objects.all().count() == 0

            # In draft state
            assert Proforma.objects.get(id=1).state == 'draft'

            # Expect 7 entries:
            # Plan Trial (+-), Plan Trial Metered Feature (+-),
            # Extra units consumed during trial (+)
            # Plan After Trial (+)
            # Metered Features After Trial (+), Plan for next month (+)
            assert DocumentEntry.objects.all().count() == 8

            doc = get_object_or_None(DocumentEntry, id=1)
            assert doc.unit_price == Decimal('57.14')

            doc = get_object_or_None(DocumentEntry, id=2)
            assert doc.unit_price == Decimal('-57.14')

            doc = get_object_or_None(DocumentEntry, id=3)
            assert doc.unit_price == metered_feature.price_per_unit
            assert doc.quantity == units_included_during_trial

            doc = get_object_or_None(DocumentEntry, id=4)
            assert doc.unit_price == - metered_feature.price_per_unit
            assert doc.quantity == units_included_during_trial

            doc = get_object_or_None(DocumentEntry, id=5)
            assert doc.unit_price == metered_feature.price_per_unit
            assert doc.quantity == units_consumed_during_trial - units_included_during_trial

            doc = get_object_or_None(DocumentEntry, id=6)
            assert doc.unit_price == Decimal('142.8600')  # 20 / 28 * 200

            doc = get_object_or_None(DocumentEntry, id=7)
            assert doc.unit_price == metered_feature.price_per_unit
            assert doc.quantity == mf_units_log_after_trial.consumed_units

            doc = get_object_or_None(DocumentEntry, id=8)
            assert doc.unit_price == Decimal('200.00')

            # And quantity 1
            assert doc.quantity == 1

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

    ###########################################################################
    # Canceled
    ###########################################################################
    def test_canceled_subscription_with_trial_and_consumed_metered_features_draft(self):
        """
        Subscription with consumed mfs both during trial and afterwards,
        canceled in the same month it started.

        start_date = 2015-02-01
        trial_end  = 2015-02-08 -- has consumed units during trial period
        end_date   = 2015-02-24 -- has consumed units between trial and end_date
        """

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
            call_command('generate_docs', billing_date=billing_date,
                         stdout=self.output)

            # Expect one Proforma
            assert Proforma.objects.all().count() == 1
            assert Invoice.objects.all().count() == 0

            # In draft state
            assert Proforma.objects.get(id=1).state == 'draft'

            # Expect 6 entries:
            # Plan Trial (+-), Plan Trial Metered Feature (+-),
            # Plan After Trial (+),  Metered Features After Trial (+)
            assert DocumentEntry.objects.all().count() == 6

            doc = get_object_or_None(DocumentEntry, id=1) # Plan trial (+)
            assert doc.unit_price == Decimal('57.14')

            doc = get_object_or_None(DocumentEntry, id=2) # Plan trial (-)
            assert doc.unit_price == Decimal('-57.14')

            doc = get_object_or_None(DocumentEntry, id=3) # Consumed mf (+)
            assert doc.unit_price == metered_feature.price_per_unit
            assert doc.quantity == mf_units_log_during_trial.consumed_units

            doc = get_object_or_None(DocumentEntry, id=4) # Consumed mf (-)
            assert doc.unit_price == - metered_feature.price_per_unit
            assert doc.quantity == mf_units_log_during_trial.consumed_units

            doc = get_object_or_None(DocumentEntry, id=5) # Plan after trial end
            assert doc.unit_price == Decimal('142.8600')  # 20 / 28 * 200

            doc = get_object_or_None(DocumentEntry, id=6) # Consumed mf after trial
            assert doc.unit_price == metered_feature.price_per_unit
            assert doc.quantity == mf_units_log_after_trial.consumed_units

    def test_canceled_subscription_with_metered_features_to_draft(self):
        """
        start_date        = 2015-01-01
        trial_end         = 2015-01-08
        last_billing_date = 2015-02-01
        """
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

        mocked_on_trial = PropertyMock(return_value=False)
        mocked_last_billing_date = PropertyMock(
            return_value=dt.date(2015, 2, 1)
        )
        mocked_is_billed_first_time = PropertyMock(return_value=False)
        with patch.multiple('silver.models.Subscription',
                            on_trial=mocked_on_trial,
                            last_billing_date=mocked_last_billing_date,
                            is_billed_first_time=mocked_is_billed_first_time):
            call_command('generate_docs', billing_date=billing_date,
                         stdout=self.output)

            # Expect one Proforma
            assert Proforma.objects.all().count() == 1
            assert Invoice.objects.all().count() == 0

            # Expect 1 entry:
            # Extra Metered Features (+)
            assert DocumentEntry.objects.all().count() == 1

            doc = get_object_or_None(DocumentEntry, id=1)
            assert doc.unit_price == metered_feature.price_per_unit
            assert doc.quantity == mf_units_log.consumed_units

    def test_canceled_subscription_with_trial_and_trial_underflow(self):
        """
        A subscription that was canceled in the same month as it started,
        the customer consuming less metered features than
        included_units_during_trial.
        """

        billing_date = '2015-03-01'

        metered_feature = MeteredFeatureFactory(
            included_units=Decimal('0.00'),
            included_units_during_trial=Decimal('5.00'))
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

        trial_quantity = Decimal('3.00')
        mf_units_log_during_trial = MeteredFeatureUnitsLogFactory(
            subscription=subscription, metered_feature=metered_feature,
            start_date=start_date, end_date=trial_end,
            consumed_units=trial_quantity)

        mf_units_log_after_trial = MeteredFeatureUnitsLogFactory(
            subscription=subscription, metered_feature=metered_feature,
            start_date=trial_end + dt.timedelta(days=1),
            # canceled 4 days before the end of the month
            end_date=dt.datetime(2015, 2, 24)
        )

        mocked_on_trial = MagicMock(return_value=False)
        with patch.multiple('silver.models.Subscription',
                            on_trial=mocked_on_trial):
            call_command('generate_docs', billing_date=billing_date,
                         stdout=self.output)

            # Expect one Proforma
            assert Proforma.objects.all().count() == 1
            assert Invoice.objects.all().count() == 0

            # In draft state
            assert Proforma.objects.get(id=1).state == 'draft'

            # Expect 6 entries:
            # Plan Trial (+-), Plan Trial Metered Feature (+-),
            # Plan After Trial (+),  Metered Features After Trial (+)
            assert DocumentEntry.objects.all().count() == 6

            doc = get_object_or_None(DocumentEntry, id=1) # Plan trial (+)
            assert doc.unit_price == Decimal('57.14')

            doc = get_object_or_None(DocumentEntry, id=2) # Plan trial (-)
            assert doc.unit_price == Decimal('-57.14')

            doc = get_object_or_None(DocumentEntry, id=3) # Consumed mf (+)
            assert doc.unit_price == metered_feature.price_per_unit
            assert doc.quantity == trial_quantity

            doc = get_object_or_None(DocumentEntry, id=4) # Consumed mf (-)
            assert doc.unit_price == - metered_feature.price_per_unit
            assert doc.quantity == trial_quantity

            doc = get_object_or_None(DocumentEntry, id=5) # Plan after trial end
            assert doc.unit_price == Decimal('142.8600')  # 20 / 28 * 200

            doc = get_object_or_None(DocumentEntry, id=6) # Consumed mf after trial
            assert doc.unit_price == metered_feature.price_per_unit
            assert doc.quantity == mf_units_log_after_trial.consumed_units

    def test_canceled_subscription_with_trial_and_trial_overflow(self):
        billing_date = '2015-03-01'

        units_included_during_trial = Decimal('5.00')
        metered_feature = MeteredFeatureFactory(
            included_units=Decimal('0.00'),
            included_units_during_trial=units_included_during_trial)
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

        units_consumed_during_trial = Decimal('7.00')
        mf_units_log_during_trial = MeteredFeatureUnitsLogFactory(
            subscription=subscription, metered_feature=metered_feature,
            start_date=start_date, end_date=trial_end,
            consumed_units=units_consumed_during_trial)

        mf_units_log_after_trial = MeteredFeatureUnitsLogFactory(
            subscription=subscription, metered_feature=metered_feature,
            start_date=trial_end + dt.timedelta(days=1),
            # canceled 4 days before the end of the month
            end_date=dt.datetime(2015, 2, 24)
        )

        mocked_on_trial = MagicMock(return_value=False)
        with patch.multiple('silver.models.Subscription',
                            on_trial=mocked_on_trial):
            call_command('generate_docs', billing_date=billing_date,
                         stdout=self.output)

            # Expect one Proforma
            assert Proforma.objects.all().count() == 1
            assert Invoice.objects.all().count() == 0

            # In draft state
            assert Proforma.objects.get(id=1).state == 'draft'

            # Expect 7 entries:
            # Plan Trial (+-), Plan Trial Metered Feature (+-),
            # Extra consumed mf
            # Plan After Trial (+),  Metered Features After Trial (+)
            assert DocumentEntry.objects.all().count() == 7

            doc = get_object_or_None(DocumentEntry, id=1) # Plan trial (+)
            assert doc.unit_price == Decimal('57.14')

            doc = get_object_or_None(DocumentEntry, id=2) # Plan trial (-)
            assert doc.unit_price == Decimal('-57.14')

            doc = get_object_or_None(DocumentEntry, id=3) # Consumed mf (+)
            assert doc.unit_price == metered_feature.price_per_unit
            assert doc.quantity == units_included_during_trial

            doc = get_object_or_None(DocumentEntry, id=4) # Consumed mf (-)
            assert doc.unit_price == - metered_feature.price_per_unit
            assert doc.quantity == units_included_during_trial

            doc = get_object_or_None(DocumentEntry, id=5) # Consumed mf (-)
            assert doc.unit_price == metered_feature.price_per_unit
            assert doc.quantity == units_consumed_during_trial - units_included_during_trial

            doc = get_object_or_None(DocumentEntry, id=6) # Plan after trial end
            assert doc.unit_price == Decimal('142.8600')  # 20 / 28 * 200

            doc = get_object_or_None(DocumentEntry, id=7) # Consumed mf after trial
            assert doc.unit_price == metered_feature.price_per_unit
            assert doc.quantity == mf_units_log_after_trial.consumed_units

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
            call_command('generate_docs', subscription='1',
                         billing_date=billing_date, stdout=self.output)

            assert Subscription.objects.filter(state='ended').count() == 1

            assert Proforma.objects.all().count() == 1
            assert Invoice.objects.all().count() == 0

            # TODO: test what's added on the proforma

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
            call_command('generate_docs', billing_date=billing_date,
                         stdout=self.output)

            # Expect 5 Proformas (2 active Subs, 3 canceled)
            assert Proforma.objects.all().count() == 5
            assert Invoice.objects.all().count() == 0

            assert Subscription.objects.filter(state='ended').count() == 3

            Proforma.objects.all().delete()

            call_command('generate_docs', billing_date=billing_date,
                         stdout=self.output)

            # Expect 2 Proformas (2 active Subs, 3 ended)
            assert Proforma.objects.all().count() == 2
