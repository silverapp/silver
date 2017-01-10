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


from django_fsm import TransitionNotAllowed
from rest_framework import serializers
from rest_framework.relations import HyperlinkedIdentityField, \
    HyperlinkedRelatedField
from rest_framework.reverse import reverse
from rest_framework.exceptions import ValidationError as APIValidationError

from django.core.exceptions import ValidationError, ObjectDoesNotExist
from silver.models.documents.document import Document
from six import iteritems

from silver.api.exceptions import APIConflictException

from silver.models import (MeteredFeatureUnitsLog, Customer, Subscription,
                           MeteredFeature, Plan, Provider, Invoice,
                           DocumentEntry, ProductCode, Proforma, PaymentMethod,
                           PaymentProcessorManager, Transaction)
from silver.validators import validate_payment_processor


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
        fields = MeteredFeatureSerializer.Meta.fields + ('url',)


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
    payment_processors = serializers.HyperlinkedIdentityField(
        view_name='provider-payment-processor-list', source='*',
        lookup_field="pk", read_only=True
    )

    class Meta:
        model = Provider
        fields = ('id', 'url', 'name', 'company', 'invoice_series', 'flow',
                  'display_email', 'notification_email', 'address_1',
                  'address_2', 'city', 'state', 'zip_code', 'country', 'extra',
                  'invoice_series', 'invoice_starting_number',
                  'proforma_series', 'proforma_starting_number', 'meta',
                  'payment_processors')

    def validate(self, data):
        data = super(ProviderSerializer, self).validate(data)

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


class ProviderUrl(HyperlinkedRelatedField):
    def get_url(self, obj, view_name, request, format):
        kwargs = {'pk': obj.pk}
        return self.reverse(view_name, kwargs=kwargs, request=request, format=format)

    def get_object(self, view_name, view_args, view_kwargs):
        return self.queryset.get(pk=view_kwargs['pk'])

    def use_pk_only_optimization(self):
        # We have the complete object instance already. We don't need
        # to run the 'only get the pk for this relationship' code.
        return False


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


class SubscriptionUrl(serializers.HyperlinkedRelatedField):
    def get_url(self, obj, view_name, request, format):
        kwargs = {'customer_pk': obj.customer.pk, 'subscription_pk': obj.pk}
        return reverse(view_name, kwargs=kwargs, request=request,
                       format=format)


class SubscriptionSerializer(serializers.HyperlinkedModelSerializer):
    trial_end = serializers.DateField(required=False)
    start_date = serializers.DateField(required=False)
    ended_at = serializers.DateField(read_only=True)
    url = SubscriptionUrl(view_name='subscription-detail', source='*',
                          queryset=Subscription.objects.all(), required=False)
    updateable_buckets = serializers.ReadOnlyField()
    meta = JSONSerializerField(required=False)
    customer = CustomerUrl(view_name='customer-detail',
                           queryset=Customer.objects.all())

    class Meta:
        model = Subscription
        fields = ('id', 'url', 'plan', 'customer', 'trial_end', 'start_date',
                  'ended_at', 'state', 'reference', 'updateable_buckets',
                  'meta', 'description')
        read_only_fields = ('state', 'updateable_buckets')

    def validate(self, attrs):
        attrs = super(SubscriptionSerializer, self).validate(attrs)

        instance = Subscription(**attrs)
        instance.clean()
        return attrs


class SubscriptionDetailSerializer(SubscriptionSerializer):
    plan = PlanSerializer(read_only=True)

    class Meta(SubscriptionSerializer.Meta):
        fields = SubscriptionSerializer.Meta.fields + ('plan',)


class CustomerSerializer(serializers.HyperlinkedModelSerializer):
    subscriptions = SubscriptionUrl(view_name='subscription-detail', many=True,
                                    read_only=True)
    payment_methods = serializers.HyperlinkedIdentityField(
        view_name='payment-method-list', source='*',
        lookup_url_kwarg='customer_pk'
    )
    transactions = serializers.HyperlinkedIdentityField(
        view_name='transaction-list', source='*',
        lookup_url_kwarg='customer_pk'
    )
    meta = JSONSerializerField(required=False)
    url = CustomerUrl(view_name='customer-detail', read_only=True, source='*')

    class Meta:
        model = Customer
        fields = ('id', 'url', 'customer_reference', 'name', 'company',
                  'emails', 'address_1', 'address_2', 'city', 'state',
                  'zip_code', 'country', 'extra', 'sales_tax_number',
                  'sales_tax_name', 'sales_tax_percent', 'consolidated_billing',
                  'subscriptions', 'payment_methods', 'transactions', 'meta')


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


class DocumentUrl(serializers.HyperlinkedIdentityField):
    def __init__(self, proforma_view_name, invoice_view_name, *args, **kwargs):
        # the view_name is required on HIF init, but we only know what it will
        # be in get_url
        kwargs['view_name'] = ''
        super(DocumentUrl, self).__init__(*args, **kwargs)

        self.invoice_view_name = invoice_view_name
        self.proforma_view_name = proforma_view_name

    def get_url(self, obj, view_name, request, format):
        view_name = (self.invoice_view_name if obj.kind =='invoice' else
                     self.proforma_view_name)

        lookup_value = getattr(obj, self.lookup_field)

        if not lookup_value:
            return

        kwargs = {
            self.lookup_url_kwarg: str(lookup_value)
        }

        return self.reverse(view_name, kwargs=kwargs,
                            request=request, format=format)


class DocumentSerializer(serializers.HyperlinkedModelSerializer):
    """
        A read-only serializers for Proformas and Invoices
    """
    customer = CustomerUrl(view_name='customer-detail',
                           queryset=Customer.objects.all())
    pdf_url = PDFUrl(view_name='', source='*', read_only=True)
    url = DocumentUrl(proforma_view_name='proforma-detail',
                      invoice_view_name='invoice-detail',)

    class Meta:
        model = Document
        fields = ('id', 'url', 'kind', 'series', 'number', 'provider',
                  'customer', 'due_date', 'issue_date', 'paid_date',
                  'cancel_date', 'sales_tax_name', 'sales_tax_percent',
                  'currency', 'state', 'total', 'pdf_url')
        read_only_fields = fields


class TransactionUrl(serializers.HyperlinkedIdentityField):
    def get_url(self, obj, view_name, request, format):
        lookup_value = getattr(obj, self.lookup_field)
        kwargs = {'transaction_uuid': str(lookup_value),
                  'customer_pk': obj.customer.pk}
        return self.reverse(view_name, kwargs=kwargs, request=request, format=format)

    def get_object(self, view_name, view_args, view_kwargs):
        return self.queryset.get(uuid=view_kwargs['transaction_uuid'])


class PaymentProcessorUrl(serializers.HyperlinkedRelatedField):
    default_validators = [validate_payment_processor]

    def __init__(self, view_name=None, **kwargs):
        super(PaymentProcessorUrl, self).__init__(view_name, **kwargs)

    def get_url(self, obj, view_name, request, format):
        lookup_value = getattr(obj, self.lookup_field)
        kwargs = {'processor_name': lookup_value}

        return self.reverse(
            view_name, kwargs=kwargs, request=request, format=format
        )

    def get_object(self, view_name, view_args, view_kwargs):
        try:
            return PaymentProcessorManager.get_instance(view_kwargs['processor_name'])
        except PaymentProcessorManager.DoesNotExist:
            raise ObjectDoesNotExist


class PDFUrl(serializers.HyperlinkedRelatedField):
    def get_url(self, obj, view_name, request, format):
        return request.build_absolute_uri(obj.pdf.url) if obj.pdf else None


class PaymentMethodUrl(serializers.HyperlinkedRelatedField):
    def get_url(self, obj, view_name, request, format):
        kwargs = {'payment_method_id': obj.pk,
                  'customer_pk': obj.customer.pk}
        return self.reverse(view_name, kwargs=kwargs, request=request, format=format)

    def get_object(self, view_name, view_args, view_kwargs):
        return self.queryset.get(id=view_kwargs['payment_method_id'])


class PaymentProcessorSerializer(serializers.Serializer):
    type = serializers.CharField(max_length=64)
    display_name = serializers.CharField(max_length=64)
    reference = serializers.CharField(max_length=256)
    url = PaymentProcessorUrl(
        view_name='payment-processor-detail', source='*', lookup_field='reference',
        read_only=True
    )


class PaymentMethodTransactionsUrl(serializers.HyperlinkedIdentityField):
    def get_url(self, obj, view_name, request, format):
        lookup_value = getattr(obj, self.lookup_field)
        kwargs = {'payment_method_id': str(lookup_value),
                  'customer_pk': obj.customer.pk}
        return self.reverse(view_name, kwargs=kwargs,
                            request=request, format=format)


class PaymentMethodSerializer(serializers.HyperlinkedModelSerializer):
    url = PaymentMethodUrl(view_name='payment-method-detail', source="*",
                           read_only=True)
    payment_processor = PaymentProcessorUrl(
        view_name='payment-processor-detail', lookup_field='reference',
        queryset=PaymentProcessorManager.all_instances())
    transactions = PaymentMethodTransactionsUrl(
        view_name='payment-method-transaction-list', source='*')
    additional_data = serializers.JSONField(required=False, write_only=True)
    customer = CustomerUrl(view_name='customer-detail', read_only=True)

    class Meta:
        model = PaymentMethod
        fields = ('url', 'transactions', 'customer', 'payment_processor',
                  'added_at', 'verified', 'enabled', 'additional_data')
        extra_kwargs = {
            'added_at': {'read_only': True},
        }

    def validate(self, attrs):
        attrs = super(PaymentMethodSerializer, self).validate(attrs)

        additional_data = attrs.get('additional_data')

        if self.instance and additional_data and not self.instance.enabled:
            message = "'additional_data' must not be given after the " \
                      "payment method has been enabled once."
            raise serializers.ValidationError(message)

        if additional_data and not attrs.get('verified', True):
            message = "If 'additional_data' is specified, then the " \
                      "payment method need to be unverified."
            raise serializers.ValidationError(message)

        return attrs

    def validate_payment_processor(self, value):
        if self.instance and value != self.instance.payment_processor:
            message = "This field may not be modified."
            raise serializers.ValidationError(message)

        return value


class TransactionSerializer(serializers.HyperlinkedModelSerializer):
    payment_method = PaymentMethodUrl(view_name='payment-method-detail',
                                      lookup_field='payment_method',
                                      queryset=PaymentMethod.objects.all())
    url = TransactionUrl(view_name='transaction-detail', lookup_field='uuid',)
    pay_url = HyperlinkedIdentityField(view_name='pay-transaction',
                                       lookup_field='uuid',
                                       lookup_url_kwarg='transaction_uuid')
    customer = CustomerUrl(view_name='customer-detail', read_only=True)
    provider = ProviderUrl(view_name='provider-detail', read_only=True)
    id = serializers.CharField(source='uuid', read_only=True)
    payment_processor = PaymentProcessorUrl(
        view_name='payment-processor-detail', lookup_field='reference',
        read_only=True
    )

    class Meta:
        model = Transaction
        fields = ('id', 'url', 'customer', 'provider', 'amount', 'currency',
                  'currency_rate_date', 'state', 'proforma', 'invoice',
                  'can_be_consumed', 'payment_processor', 'payment_method',
                  'pay_url', 'valid_until', 'success_url', 'failed_url')
        read_only_fields = ('customer', 'provider', 'can_be_consumed', 'pay_url',
                            'id', 'url', 'state')
        write_only_fields = ('valid_until',)

    def validate_proforma(self, proforma):
        if self.instance and proforma != self.instance.proforma:
            message = "This field may not be modified."
            raise serializers.ValidationError(message)

        return proforma

    def validate_invoice(self, invoice):
        if self.instance and invoice != self.instance.invoice:
            message = "This field may not be modified."
            raise serializers.ValidationError(message)
        if (self.instance and getattr(self.instance, 'transactions', None) and
           self.instance.transaction_set.exclude(state='canceled').exists()):
            message = "Cannot update a payment with active transactions."
            raise serializers.ValidationError(message)

        return invoice

    def validate(self, attrs):
        attrs = super(TransactionSerializer, self).validate(attrs)

        if not attrs:
            return attrs

        if self.instance:
            if self.instance.state != Transaction.States.Initial:
                message = "The transaction cannot be modified once it is in {}"\
                          " state.".format(self.instance.state)
                raise serializers.ValidationError(message)

        # Run model clean and handle ValidationErrors
        try:
            # Use the existing instance to avoid unique field errors
            if self.instance:
                transaction = self.instance
                transaction_dict = transaction.__dict__.copy()

                for attribute, value in attrs.items():
                    setattr(transaction, attribute, value)

                transaction.full_clean()

                # Revert changes to existing instance
                transaction.__dict__ = transaction_dict
            else:
                transaction = Transaction(**attrs)
                transaction.full_clean()
        except ValidationError as e:
            errors = e.error_dict
            non_field_errors = errors.pop('__all__', None)
            if non_field_errors:
                errors['non_field_errors'] = [
                    error for sublist in non_field_errors for error in sublist
                ]

            raise serializers.ValidationError(errors)

        return attrs


class InvoiceSerializer(serializers.HyperlinkedModelSerializer):
    invoice_entries = DocumentEntrySerializer(many=True)
    pdf_url = PDFUrl(view_name='', source='*', read_only=True)
    customer = CustomerUrl(view_name='customer-detail',
                           queryset=Customer.objects.all())
    transactions = TransactionSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = ('id', 'series', 'number', 'provider', 'customer',
                  'archived_provider', 'archived_customer', 'due_date',
                  'issue_date', 'paid_date', 'cancel_date', 'sales_tax_name',
                  'sales_tax_percent', 'currency', 'state', 'proforma',
                  'invoice_entries', 'total', 'pdf_url', 'transactions')
        read_only_fields = ('archived_provider', 'archived_customer', 'total')

    def create(self, validated_data):
        entries = validated_data.pop('invoice_entries', None)

        # Create the new invoice object
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
        data = super(InvoiceSerializer, self).validate(data)

        if self.instance:
            self.instance.clean()

        if self.instance and data['state'] != self.instance.state:
            msg = "Direct state modification is not allowed." \
                  " Use the corresponding endpoint to update the state."
            raise serializers.ValidationError(msg)
        return data


class ProformaSerializer(serializers.HyperlinkedModelSerializer):
    proforma_entries = DocumentEntrySerializer(many=True)
    pdf_url = PDFUrl(view_name='', source='*', read_only=True)
    customer = CustomerUrl(view_name='customer-detail',
                           queryset=Customer.objects.all())
    transactions = TransactionSerializer(many=True, read_only=True)

    class Meta:
        model = Proforma
        fields = ('id', 'series', 'number', 'provider', 'customer',
                  'archived_provider', 'archived_customer', 'due_date',
                  'issue_date', 'paid_date', 'cancel_date', 'sales_tax_name',
                  'sales_tax_percent', 'currency', 'state', 'invoice',
                  'proforma_entries', 'total', 'pdf_url', 'transactions')
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
        data = super(ProformaSerializer, self).validate(data)

        if self.instance:
            self.instance.clean()

        if self.instance and data['state'] != self.instance.state:
            msg = "Direct state modification is not allowed." \
                  " Use the corresponding endpoint to update the state."
            raise serializers.ValidationError(msg)
        return data
