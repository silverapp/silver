from rest_framework import serializers
from rest_framework.reverse import reverse
from rest_framework.relations import HyperlinkedRelatedField

from django.conf import settings

from silver.api.serializers.product_codes_serializer import ProductCodeRelatedField
from silver.models import MeteredFeature


class CustomerUrl(HyperlinkedRelatedField):
    def get_url(self, obj, view_name, request, format):
        kwargs = {'customer_pk': obj.pk}
        return self.reverse(view_name, kwargs=kwargs, request=request, format=format)

    def get_object(self, view_name, view_args, view_kwargs):
        return self.queryset.get(pk=view_kwargs['customer_pk'])

    def use_pk_only_optimization(self):
        # We have the complete object instance already. We don't need
        # to run the 'only get the pk for this relationship' code.
        return False


class PaymentMethodTransactionsUrl(serializers.HyperlinkedIdentityField):
    def get_url(self, obj, view_name, request, format):
        lookup_value = getattr(obj, self.lookup_field)
        kwargs = {'payment_method_id': str(lookup_value),
                  'customer_pk': obj.customer_id}
        return self.reverse(view_name, kwargs=kwargs,
                            request=request, format=format)


class MeteredFeatureSerializer(serializers.ModelSerializer):
    product_code = ProductCodeRelatedField()

    class Meta:
        model = MeteredFeature
        fields = ('name', 'unit', 'price_per_unit', 'included_units',
                  'product_code')

    def create(self, validated_data):
        product_code = validated_data.pop('product_code')
        product_code.save()

        validated_data.update({'product_code': product_code})

        metered_feature = MeteredFeature.objects.create(**validated_data)

        return metered_feature


class PDFUrl(serializers.HyperlinkedRelatedField):
    def get_url(self, obj, view_name, request, format):
        if not (obj.pdf and obj.pdf.url):
            return None

        if getattr(settings, 'SILVER_SHOW_PDF_STORAGE_URL', True):
            return request.build_absolute_uri(obj.pdf.url)

        return self.reverse(view_name, kwargs={'pdf_pk': obj.pdf.pk},
                            request=request, format=format)
