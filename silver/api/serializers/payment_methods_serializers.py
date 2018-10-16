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

from __future__ import absolute_import

from django.core.exceptions import ObjectDoesNotExist, ValidationError, NON_FIELD_ERRORS

from rest_framework import serializers

from silver import payment_processors
from silver.api.serializers.common import CustomerUrl, PaymentMethodTransactionsUrl
from silver.models import PaymentMethod


class PaymentProcessorUrl(serializers.HyperlinkedRelatedField):
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
            return payment_processors.get_instance(view_kwargs['processor_name'])
        except ImportError:
            raise ObjectDoesNotExist


class PaymentMethodUrl(serializers.HyperlinkedRelatedField):
    def get_url(self, obj, view_name, request, format):
        kwargs = {'payment_method_id': obj.pk,
                  'customer_pk': obj.customer_id}
        return self.reverse(view_name, kwargs=kwargs, request=request, format=format)

    def get_object(self, view_name, view_args, view_kwargs):
        return self.queryset.get(id=view_kwargs['payment_method_id'])


class PaymentMethodSerializer(serializers.HyperlinkedModelSerializer):
    url = PaymentMethodUrl(view_name='payment-method-detail', source="*",
                           read_only=True)
    transactions = PaymentMethodTransactionsUrl(
        view_name='payment-method-transaction-list', source='*')
    payment_processor_name = serializers.ModelField(
        model_field=PaymentMethod()._meta.get_field('payment_processor'),
        source="payment_processor",
        label="Payment Processor"
    )
    payment_processor = serializers.SerializerMethodField()

    def get_payment_processor(self, obj):
        return PaymentProcessorSerializer(obj.get_payment_processor(),
                                          context=self.context).data

    class Meta:
        model = PaymentMethod
        fields = ('url', 'transactions', 'customer', 'payment_processor_name',
                  'payment_processor', 'added_at', 'verified',
                  'canceled', 'valid_until', 'display_info')
        extra_kwargs = {
            'added_at': {'read_only': True},
            'customer': {'read_only': True, 'lookup_url_kwarg': 'customer_pk'}
        }

    def validate(self, attrs):
        attrs = super(PaymentMethodSerializer, self).validate(attrs)

        if self.instance:
            if self.instance.canceled:
                raise ValidationError(
                    'You cannot update a canceled payment method.'
                )

            # Run model clean and handle ValidationErrors
            try:
                # Use the existing instance to avoid unique field errors
                payment_method = self.instance
                payment_method_dict = payment_method.__dict__.copy()

                for attribute, value in attrs.items():
                    setattr(payment_method, attribute, value)

                payment_method.full_clean()

                # Revert changes to existing instance
                payment_method.__dict__ = payment_method_dict
            except ValidationError as e:
                errors = e.error_dict
                non_field_errors = errors.pop(NON_FIELD_ERRORS, None)
                if non_field_errors:
                    errors['non_field_errors'] = [
                        error for sublist in non_field_errors for error in sublist
                    ]
                raise serializers.ValidationError(errors)

        return attrs

    def validate_payment_processor_name(self, value):
        if value not in PaymentMethod.PaymentProcessors.as_list():
            raise serializers.ValidationError('"{}" is not a valid '
                                              'choice'.format(value))
        if self.instance and value != self.instance.payment_processor:
            message = "This field may not be modified."
            raise serializers.ValidationError(message)

        return value

    def validate_verified(self, value):
        if self.instance and not value and self.instance.verified:
            message = "You cannot unverify a payment method."
            raise serializers.ValidationError(message)

        return value


class PaymentProcessorSerializer(serializers.Serializer):
    type = serializers.CharField(max_length=64)
    name = serializers.CharField(max_length=64)
    allowed_currencies = serializers.ListField()
    url = PaymentProcessorUrl(
        view_name='payment-processor-detail', source='*', lookup_field='name',
        read_only=True
    )
