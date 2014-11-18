import factory

from django.contrib.auth import get_user_model
from international.models import countries

from silver.models import Provider, Plan, INTERVALS, MeteredFeature, Customer


class CustomerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Customer

    factory.Sequence(lambda n: 'Reference{cnt}'.format(cnt=n))
    sales_tax_percent = factory.Sequence(lambda n: n)
    sales_tax_name = factory.Sequence(lambda n: 'Tax{cnt}'.format(cnt=n))
    consolidated_billing = factory.Sequence(lambda n: n % 2 == 1)
    name = factory.Sequence(lambda n: 'Name{cnt}'.format(cnt=n))
    company = factory.Sequence(lambda n: 'Company{cnt}'.format(cnt=n))
    email = factory.Sequence(lambda n: 'some{cnt}@email.com'.format(cnt=n))
    address_1 = factory.Sequence(lambda n: 'Address1{cnt}'.format(cnt=n))
    address_2 = factory.Sequence(lambda n: 'Address2{cnt}'.format(cnt=n))
    country = factory.Sequence(lambda n: countries[n])
    city = factory.Sequence(lambda n: 'City{cnt}'.format(cnt=n))
    state = factory.Sequence(lambda n: 'State{cnt}'.format(cnt=n))
    zip_code = factory.Sequence(lambda n: n)
    extra = factory.Sequence(lambda n: 'Extra{cnt}'.format(cnt=n))


class MeteredFeatureFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MeteredFeature

    name = factory.Sequence(lambda n: 'Name{cnt}'.format(cnt=n))
    price_per_unit = factory.Sequence(lambda n: n)
    included_units = factory.Sequence(lambda n: n)


class ProviderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Provider

    name = factory.Sequence(lambda n: 'Provider{cnt}'.format(cnt=n))
    company = factory.Sequence(lambda n: 'Company{cnt}'.format(cnt=n))
    address_1 = factory.Sequence(lambda n: 'Address_1{cnt}'.format(cnt=n))
    country = 'RO'
    city = factory.Sequence(lambda n: 'City{cnt}'.format(cnt=n))
    zip_code = factory.Sequence(lambda n: '{cnt}'.format(cnt=n))


class PlanFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Plan

    name = factory.Sequence(lambda n: 'Name{cnt}'.format(cnt=n))
    interval = factory.Sequence(lambda n: INTERVALS[n % 4])
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


class AdminUserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_user_model()

    username = 'admin'
    email = 'admin@admin.com'
    password = factory.PostGenerationMethodCall('set_password', 'admin')
    is_active = True
    is_superuser = True
    is_staff = True
