# Copyright (c) 2015 Presslabs SRL
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from django.core.exceptions import ValidationError, ObjectDoesNotExist
from rest_framework import serializers
from rest_framework.reverse import reverse

from silver.models import (MeteredFeatureUnitsLog, Customer, Subscription,
                           MeteredFeature, Plan, Provider, Invoice,
                           DocumentEntry, ProductCode, Proforma)


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


class MFUnitsLogUrl(serializers.HyperlinkedRelatedField):
    def get_url(self, obj, view_name, request, format):
        customer_pk = request.parser_context['kwargs']['customer_pk']
        subscription_pk = request.parser_context['kwargs']['subscription_pk']
        kwargs = {
            'customer_pk': customer_pk,
            'subscription_pk': subscription_pk,
            'mf_product_code': obj.product_code.value
        }
        return self.reverse(view_name, kwargs=kwargs, request=request,
                            format=format)


class MeteredFeatureInSubscriptionSerializer(MeteredFeatureSerializer):
    url = MFUnitsLogUrl(view_name='mf-log-units', source='*', read_only=True)

    class Meta(MeteredFeatureSerializer.Meta):
        fields = MeteredFeatureSerializer.Meta.fields + ('url', )


class MFUnitsLogSerializer(serializers.HyperlinkedModelSerializer):
    # The 2 lines below are needed because of a DRF3 bug
    start_date = serializers.DateField(read_only=True)
    end_date = serializers.DateField(read_only=True)

    class Meta:
        model = MeteredFeatureUnitsLog
        fields = ('consumed_units', 'start_date', 'end_date')


class JSONSerializerField(serializers.Field):
    def to_internal_value(self, data):
        if not data:
            return data

        if (data is not None and not isinstance(data, dict) and
                not isinstance(data, list)):
                    raise ValidationError("Invalid JSON <{}>".format(data))
        return data

    def to_representation(self, value):
        return value


class ProviderSerializer(serializers.HyperlinkedModelSerializer):
    meta = JSONSerializerField(required=False)

    class Meta:
        model = Provider
        fields = ('id', 'url', 'name', 'company', 'invoice_series', 'flow',
                  'email', 'address_1', 'address_2', 'city', 'state',
                  'zip_code', 'country', 'extra', 'invoice_series',
                  'invoice_starting_number', 'proforma_series',
                  'proforma_starting_number', 'meta')

    def validate(self, data):
        flow = data.get('flow', None)
        if flow == Provider.FLOWS.PROFORMA:
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
            mf = MeteredFeatureSerializer(data=mf_data)
            mf.is_valid(raise_exception=True)
            mf = mf.create(mf.validated_data)
            metered_features.append(mf)

        product_code = validated_data.pop('product_code')
        product_code.save()

        validated_data.update({'product_code': product_code})

        plan = Plan.objects.create(**validated_data)
        plan.metered_features.add(*metered_features)
        plan.product_code = product_code

        plan.save()

        return plan

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.generate_after = validated_data.get('generate_after',
                                                     instance.generate_after)
        instance.due_days = validated_data.get('due_days', instance.due_days)
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
    updateable_buckets = serializers.ReadOnlyField()
    meta = JSONSerializerField(required=False)

    class Meta:
        model = Subscription
        fields = ('id', 'url', 'plan', 'customer', 'trial_end', 'start_date',
                  'ended_at', 'state', 'reference', 'updateable_buckets',
                  'meta', 'description')
        read_only_fields = ('state', 'updateable_buckets')

    def validate(self, attrs):
        instance = Subscription(**attrs)
        instance.clean()
        return attrs


class SubscriptionDetailSerializer(SubscriptionSerializer):
    plan = PlanSerializer(read_only=True)

    class Meta(SubscriptionSerializer.Meta):
        fields = SubscriptionSerializer.Meta.fields + ('plan', )


class CustomerSerializer(serializers.HyperlinkedModelSerializer):
    subscriptions = SubscriptionUrl(view_name='subscription-detail', many=True,
                                    read_only=True)
    meta = JSONSerializerField(required=False)

    class Meta:
        model = Customer
        fields = ('id', 'url', 'customer_reference', 'name', 'company', 'email',
                  'address_1', 'address_2', 'city', 'state', 'zip_code',
                  'country', 'extra', 'sales_tax_number', 'sales_tax_name',
                  'sales_tax_percent', 'consolidated_billing', 'subscriptions',
                  'meta')


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
        fields = ('description', 'unit', 'unit_price', 'quantity', 'total',
                  'total_before_tax', 'start_date', 'end_date', 'prorated',
                  'product_code')


class PDFUrl(serializers.HyperlinkedRelatedField):
    def get_url(self, obj, view_name, request, format):
        return request.build_absolute_uri(obj.pdf.url) if obj.pdf else None


class InvoiceSerializer(serializers.HyperlinkedModelSerializer):
    invoice_entries = DocumentEntrySerializer(many=True)
    pdf_url = PDFUrl(view_name='', source='*', read_only=True)

    class Meta:
        model = Invoice
        fields = ('id', 'series', 'number', 'provider', 'customer',
                  'archived_provider', 'archived_customer', 'due_date',
                  'issue_date', 'paid_date', 'cancel_date', 'sales_tax_name',
                  'sales_tax_percent', 'currency', 'state', 'proforma',
                  'invoice_entries', 'total', 'pdf_url')
        read_only_fields = ('archived_provider', 'archived_customer', 'total')

    def create(self, validated_data):
        entries = validated_data.pop('invoice_entries', None)

        # Create the new invoice objectj
        invoice = Invoice.objects.create(**validated_data)

        # Add the invoice entries
        for entry in entries:
            entry_dict = dict()
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
    pdf_url = PDFUrl(view_name='', source='*', read_only=True)

    class Meta:
        model = Proforma
        fields = ('id', 'series', 'number', 'provider', 'customer',
                  'archived_provider', 'archived_customer', 'due_date',
                  'issue_date', 'paid_date', 'cancel_date', 'sales_tax_name',
                  'sales_tax_percent', 'currency', 'state', 'invoice',
                  'proforma_entries', 'total', 'pdf_url')
        read_only_fields = ('archived_provider', 'archived_customer', 'total')

    def create(self, validated_data):
        entries = validated_data.pop('proforma_entries', None)

        proforma = Proforma.objects.create(**validated_data)

        for entry in entries:
            entry_dict = dict()
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
