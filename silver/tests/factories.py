import factory

from silver.models import Provider


class ProviderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Provider
