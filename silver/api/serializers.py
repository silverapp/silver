from django.core.exceptions import ValidationError, ObjectDoesNotExist
from rest_framework import serializers
from rest_framework.reverse import reverse

from silver.models import (MeteredFeatureUnitsLog, Customer, Subscription,
                           MeteredFeature, Plan, Provider, Invoice,
                           DocumentEntry, ProductCode, Proforma)


class MFUnitsLogUrl(serializers.HyperlinkedRelatedField):
    def get_url(self, obj, view_name, request, format):
        customer_pk = request.parser_context['kwargs']['customer_pk']
        subscription_pk = request.parser_context['kwargs']['subscription_pk']
        kwargs = {
            'customer_pk': customer_pk,
            'subscription_pk': subscription_pk,
            'mf_product_code': obj.product_code.value
        }
        return self.reverse(view_name, kwargs=kwargs, request=request, format=format)


class MeteredFeatureSerializer(serializers.ModelSerializer):
    product_code = serializers.SlugRelatedField(
        slug_field='value',
        queryset=ProductCode.objects.all()
    )

    class Meta:
        model = MeteredFeature
        fields = ('name', 'unit', 'price_per_unit', 'included_units',
                  'product_code')


class MeteredFeatureRelatedField(serializers.HyperlinkedRelatedField):
    def get_url(self, obj, view_name, request, format):
        kwargs = {'pk': obj.pk}
        return reverse(view_name, kwargs=kwargs, request=request, format=format)

    def to_native(self, obj):
        request = self.context.get('request', None)
        return MeteredFeatureSerializer(obj, context={'request': request}).data


class MeteredFeatureInSubscriptionSerializer(serializers.HyperlinkedModelSerializer):
    url = MFUnitsLogUrl(view_name='mf-log-units', source='*', read_only=True)

    product_code = serializers.SlugRelatedField(
        slug_field='value',
        queryset=ProductCode.objects.all()
    )

    class Meta:
        model = MeteredFeature
        fields = ('name', 'unit', 'price_per_unit', 'included_units',
                  'product_code', 'url')


class MeteredFeatureUnitsLogSerializer(serializers.HyperlinkedModelSerializer):
    # The 2 lines below are needed because of a DRF3 bug
    start_date = serializers.DateField(read_only=True)
    end_date = serializers.DateField(read_only=True)

    class Meta:
        model = MeteredFeatureUnitsLog
        fields = ('consumed_units', 'start_date', 'end_date')


class ProviderSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Provider
        fields = ('id', 'url', 'name', 'company', 'invoice_series', 'flow',
                  'email', 'address_1', 'address_2', 'city', 'state',
                  'zip_code', 'country', 'extra', 'invoice_series',
                  'invoice_starting_number', 'proforma_series',
                  'proforma_starting_number')

    def validate(self, data):
        if data['flow'] == 'proforma':
            if not data.get('proforma_starting_number', None) and\
               not data.get('proforma_series', None):
                errors = {'proforma_series': "This field is required as the "
                                             "chosen flow is proforma.",
                          'proforma_starting_number': "This field is required "
                                                      "as the chosen flow is "
                                                      "proforma."}
                raise serializers.ValidationError(errors)
            elif not data.get('proforma_series'):
                errors = {'proforma_series': "This field is required as the "
                                             "chosen flow is proforma."}
                raise serializers.ValidationError(errors)
            elif not data.get('proforma_starting_number', None):
                errors = {'proforma_starting_number': "This field is required "
                                                      "as the chosen flow is "
                                                      "proforma."}
                raise serializers.ValidationError(errors)

        return data


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


class PlanSerializer(serializers.HyperlinkedModelSerializer):
    metered_features = MeteredFeatureSerializer(
        required=False, many=True
    )
    provider = serializers.HyperlinkedRelatedField(
        queryset=Provider.objects.all(),
        view_name='provider-detail',
    )
    product_code = ProductCodeRelatedField()

    class Meta:
        model = Plan
        fields = ('name', 'url', 'interval', 'interval_count', 'amount',
                  'currency', 'trial_period_days', 'generate_after', 'enabled',
                  'private', 'product_code', 'metered_features', 'provider')

    def validate_metered_features(self, value):
        metered_features = []
        for mf_data in value:
            metered_features.append(MeteredFeature(**mf_data))

        try:
            Plan.validate_metered_features(metered_features)
        except ValidationError, e:
            raise serializers.ValidationError(str(e)[3:-2])

        return value

    def create(self, validated_data):
        metered_features_data = validated_data.pop('metered_features')
        metered_features = []
        for mf_data in metered_features_data:
            metered_features.append(MeteredFeature.objects.create(**mf_data))

        product_code = validated_data.pop('product_code')
        product_code = ProductCode.objects.get_or_create(value=product_code)[0]

        validated_data.update({'product_code': product_code})

        plan = Plan.objects.create(**validated_data)
        plan.metered_features.add(*metered_features)
        plan.product_code = product_code

        plan.save()

        return plan

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.generate_after = validated_data.get('generate_after', instance.generate_after)
        instance.save()

        return instance


class SubscriptionUrl(serializers.HyperlinkedRelatedField):
    def get_url(self, obj, view_name, request, format):
        kwargs = {'customer_pk': obj.customer.pk, 'subscription_pk': obj.pk}
        return reverse(view_name, kwargs=kwargs, request=request, format=format)


class SubscriptionSerializer(serializers.HyperlinkedModelSerializer):
    trial_end = serializers.DateField(required=False)
    start_date = serializers.DateField(required=False)
    ended_at = serializers.DateField(read_only=True)
    url = SubscriptionUrl(view_name='subscription-detail', source='*',
                          queryset=Subscription.objects.all(), required=False)

    class Meta:
        model = Subscription
        fields = ('url', 'plan', 'customer', 'trial_end', 'start_date',
                  'ended_at', 'state', 'reference')
        read_only_fields = ('state', )

    def validate(self, attrs):
        instance = Subscription(**attrs)
        instance.clean()
        return attrs


class SubscriptionDetailSerializer(SubscriptionSerializer):
    metered_features = MeteredFeatureInSubscriptionSerializer(
        source='plan.metered_features', many=True, read_only=True
    )

    class Meta(SubscriptionSerializer.Meta):
        fields = SubscriptionSerializer.Meta.fields + ('metered_features',)


class CustomerSerializer(serializers.HyperlinkedModelSerializer):
    subscriptions = SubscriptionUrl(view_name='subscription-detail', many=True,
                                    read_only=True)

    class Meta:
        model = Customer
        fields = ('url', 'customer_reference', 'name', 'company', 'email',
                  'address_1', 'address_2', 'city', 'state', 'zip_code',
                  'country', 'extra', 'sales_tax_number', 'sales_tax_name',
                  'sales_tax_percent', 'subscriptions')


class ProductCodeSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ProductCode
        fields = ('url', 'value')


class DocumentEntrySerializer(serializers.HyperlinkedModelSerializer):
    product_code = serializers.SlugRelatedField(
        slug_field='value',
        read_only=True
    )

    class Meta:
        model = DocumentEntry
        fields = ('entry_id', 'description', 'unit', 'unit_price', 'quantity',
                  'total', 'start_date', 'end_date', 'prorated', 'product_code')


class InvoiceSerializer(serializers.HyperlinkedModelSerializer):
    invoice_entries = DocumentEntrySerializer(many=True)

    class Meta:
        model = Invoice
        fields = ('id', 'series', 'number', 'provider', 'customer',
                  'archived_provider', 'archived_customer', 'due_date',
                  'issue_date', 'paid_date', 'cancel_date', 'sales_tax_name',
                  'sales_tax_percent', 'currency', 'state', 'proforma',
                  'invoice_entries', 'total')
        read_only_fields = ('archived_provider', 'archived_customer', 'total')

    def create(self, validated_data):
        entries = validated_data.pop('invoice_entries', None)

        # Create the new invoice objectj
        invoice = Invoice.objects.create(**validated_data)

        # Add the invoice entries
        for entry in entries:
            entry_dict = {}
            entry_dict['invoice'] = invoice
            for field in entry.items():
                entry_dict[field[0]] = field[1]

            DocumentEntry.objects.create(**entry_dict)

        return invoice

    def update(self, instance, validated_data):
        # The provider has changed => force the generation of the correct number
        # corresponding to the count of the new provider
        current_provider = instance.provider
        new_provider = validated_data.get('provider')
        if new_provider and new_provider != current_provider:
            instance.number = None

        updateable_fields = instance.updateable_fields
        for field_name in updateable_fields:
            field_value = validated_data.get(field_name,
                                             getattr(instance, field_name))
            setattr(instance, field_name, field_value)
        instance.save()

        return instance

    def validate(self, data):
        if self.instance:
            self.instance.clean()

        if self.instance and data['state'] != self.instance.state:
            msg = "Direct state modification is not allowed."\
                  " Use the corresponding endpoint to update the state."
            raise serializers.ValidationError(msg)
        return data


class ProformaSerializer(serializers.HyperlinkedModelSerializer):
    proforma_entries = DocumentEntrySerializer(many=True)

    class Meta:
        model = Proforma
        fields = ('id', 'series', 'number', 'provider', 'customer',
                  'archived_provider', 'archived_customer', 'due_date',
                  'issue_date', 'paid_date', 'cancel_date', 'sales_tax_name',
                  'sales_tax_percent', 'currency', 'state', 'invoice',
                  'proforma_entries', 'total')
        read_only_fields = ('archived_provider', 'archived_customer', 'total')

    def create(self, validated_data):
        entries = validated_data.pop('proforma_entries', None)

        proforma = Proforma.objects.create(**validated_data)

        for entry in entries:
            entry_dict = {}
            entry_dict['proforma'] = proforma
            for field in entry.items():
                entry_dict[field[0]] = field[1]

            DocumentEntry.objects.create(**entry_dict)

        return proforma

    def update(self, instance, validated_data):
        # The provider has changed => force the generation of the correct number
        # corresponding to the count of the new provider
        current_provider = instance.provider
        new_provider = validated_data.get('provider')
        if new_provider and new_provider != current_provider:
            instance.number = None

        updateable_fields = instance.updateable_fields
        for field_name in updateable_fields:
            field_value = validated_data.get(field_name,
                                             getattr(instance, field_name))
            setattr(instance, field_name, field_value)
        instance.save()

        return instance

    def validate(self, data):
        if self.instance:
            self.instance.clean()

        if self.instance and data['state'] != self.instance.state:
            msg = "Direct state modification is not allowed."\
                  " Use the corresponding endpoint to update the state."
            raise serializers.ValidationError(msg)
        return data
