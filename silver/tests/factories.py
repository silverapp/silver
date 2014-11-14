import factory

from django.contrib.auth import get_user_model

from silver.models import Provider


class ProviderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Provider

    name = factory.Sequence(lambda n: 'Provider{cnt}'.format(cnt=n))
    company = factory.Sequence(lambda n: 'Company{cnt}'.format(cnt=n))
    address_1 = factory.Sequence(lambda n: 'Address_1{cnt}'.format(cnt=n))
    country = 'RO'
    city = factory.Sequence(lambda n: 'City{cnt}'.format(cnt=n))
    zip_code = factory.Sequence(lambda n: '{cnt}'.format(cnt=n))


class AdminUserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_user_model()

    username = 'admin'
    email = 'admin@admin.com'
    password = factory.PostGenerationMethodCall('set_password', 'admin')
    is_active = True
    is_superuser = True
    is_staff = True

