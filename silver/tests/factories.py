import datetime

import factory
import factory.fuzzy
from django.contrib.auth import get_user_model
from international.models import countries

from silver.models import (Provider, Plan, MeteredFeature, Customer,
                           Subscription)


class CustomerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Customer

    name = factory.Sequence(lambda n: 'Name{cnt}'.format(cnt=n))
    company = factory.Sequence(lambda n: 'Company{cnt}'.format(cnt=n))
    email = factory.Sequence(lambda n: 'some{cnt}@email.com'.format(cnt=n))
    address_1 = factory.Sequence(lambda n: 'Address1{cnt}'.format(cnt=n))
    address_2 = factory.Sequence(lambda n: 'Address2{cnt}'.format(cnt=n))
    country = factory.Sequence(lambda n: countries[n][0])
    city = factory.Sequence(lambda n: 'City{cnt}'.format(cnt=n))
    state = factory.Sequence(lambda n: 'State{cnt}'.format(cnt=n))
    zip_code = factory.Sequence(lambda n: str(n))
    extra = factory.Sequence(lambda n: 'Extra{cnt}'.format(cnt=n))

    customer_reference = factory.Sequence(lambda n: 'Reference{cnt}'.format(cnt=n))
    sales_tax_percent = factory.fuzzy.FuzzyDecimal(1.0, 19.0)
    sales_tax_name = factory.Sequence(lambda n: 'VTA'.format(cnt=n))


class MeteredFeatureFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MeteredFeature

    name = factory.Sequence(lambda n: 'Name{cnt}'.format(cnt=n))
    price_per_unit = factory.Sequence(lambda n: n)
    included_units = factory.Sequence(lambda n: n)


class ProviderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Provider

    name = factory.Sequence(lambda n: 'Name{cnt}'.format(cnt=n))
    company = factory.Sequence(lambda n: 'Company{cnt}'.format(cnt=n))
    email = factory.Sequence(lambda n: 'some{cnt}@email.com'.format(cnt=n))
    address_1 = factory.Sequence(lambda n: 'Address1{cnt}'.format(cnt=n))
    address_2 = factory.Sequence(lambda n: 'Address2{cnt}'.format(cnt=n))
    country = factory.Sequence(lambda n: countries[n][0])
    city = factory.Sequence(lambda n: 'City{cnt}'.format(cnt=n))
    state = factory.Sequence(lambda n: 'State{cnt}'.format(cnt=n))
    zip_code = factory.Sequence(lambda n: str(n))
    extra = factory.Sequence(lambda n: 'Extra{cnt}'.format(cnt=n))

    flow = 'proforma'
    invoice_series = 'InvoiceSeries'
    invoice_starting_number = 1
    proforma_series = 'ProformaSeries'
    proforma_starting_number = 1


class PlanFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Plan

    name = factory.Sequence(lambda n: 'Name{cnt}'.format(cnt=n))
    interval = factory.Sequence(lambda n: Plan.INTERVALS[n % 4][0])
    interval_count = factory.Sequence(lambda n: n)
    amount = factory.Sequence(lambda n: n)
    currency = 'USD'
    trial_period_days = factory.Sequence(lambda n: n)
    due_days = factory.Sequence(lambda n: n)
    generate_after = factory.Sequence(lambda n: n)
    enabled = factory.Sequence(lambda n: n % 2 != 0)
    private = factory.Sequence(lambda n: n % 2 != 0)
    product_code = factory.Sequence(lambda n: '{cnt}'.format(cnt=n))
    provider = factory.SubFactory(ProviderFactory)

    @factory.post_generation
    def metered_features(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            # A list of groups were passed in, use them
            for metered_feature in extracted:
                self.metered_features.add(metered_feature)


class SubscriptionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Subscription

    plan = factory.SubFactory(PlanFactory)
    customer = factory.SubFactory(CustomerFactory)
    trial_end = factory.Sequence(lambda n: datetime.date.today() +
                                 datetime.timedelta(days=n))
    start_date = datetime.date.today()


class AdminUserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_user_model()

    username = 'admin'
    email = 'admin@admin.com'
    password = factory.PostGenerationMethodCall('set_password', 'admin')
    is_active = True
    is_superuser = True
    is_staff = True
