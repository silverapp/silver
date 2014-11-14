import factory

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
