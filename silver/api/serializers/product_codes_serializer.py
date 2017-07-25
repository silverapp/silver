from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from silver.models import ProductCode


class ProductCodeRelatedField(serializers.SlugRelatedField):
    def __init__(self, **kwargs):
        super(ProductCodeRelatedField, self).__init__(
            slug_field='value', queryset=ProductCode.objects.all(), **kwargs)

    def to_internal_value(self, data):
        try:
            return ProductCode.objects.get(**{self.slug_field: data})
        except ObjectDoesNotExist:
            return ProductCode(**{self.slug_field: data})
        except (TypeError, ValueError):
            self.fail('invalid')


class ProductCodeSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ProductCode
        fields = ('url', 'value')
