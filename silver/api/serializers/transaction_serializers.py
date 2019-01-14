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

import jwt

from django.conf import settings
from django.core.exceptions import ValidationError, NON_FIELD_ERRORS as DJANGO_NON_FIELD_ERRORS

from rest_framework import serializers
from rest_framework.settings import api_settings

from silver.api.serializers.billing_entities_serializers import ProviderUrl
from silver.api.serializers.common import CustomerUrl
from silver.api.serializers.payment_methods_serializers import PaymentMethodUrl
from silver.models import PaymentMethod, Transaction
from silver.utils.payments import get_payment_url
from silver.utils.serializers import AutoCleanSerializerMixin


class TransactionUrl(serializers.HyperlinkedIdentityField):
    def get_url(self, obj, view_name, request, format):
        lookup_value = getattr(obj, self.lookup_field)
        kwargs = {'transaction_uuid': str(lookup_value),
                  'customer_pk': obj.customer.pk}
        return self.reverse(view_name, kwargs=kwargs, request=request, format=format)

    def get_object(self, view_name, view_args, view_kwargs):
        return self.queryset.get(uuid=view_kwargs['transaction_uuid'])


class TransactionPaymentUrl(serializers.HyperlinkedIdentityField):
    def get_url(self, obj, view_name, request, format):
        if not obj.can_be_consumed:
            return None
        return get_payment_url(obj, request)

    def get_object(self, view_name, view_args, view_kwargs):
        try:
            transaction_uuid = jwt.decode(view_kwargs['token'],
                                          settings.PAYMENT_METHOD_SECRET)['transaction']
            return self.queryset.get(uuid=transaction_uuid)
        except (jwt.ExpiredSignatureError, jwt.DecodeError, jwt.InvalidTokenError):
            return None


class TransactionSerializer(AutoCleanSerializerMixin,
                            serializers.HyperlinkedModelSerializer):
    payment_method = PaymentMethodUrl(view_name='payment-method-detail',
                                      lookup_field='payment_method',
                                      queryset=PaymentMethod.objects.all())
    url = TransactionUrl(view_name='transaction-detail', lookup_field='uuid', )
    pay_url = TransactionPaymentUrl(lookup_url_kwarg='token',
                                    view_name='payment')
    customer = CustomerUrl(view_name='customer-detail', read_only=True)
    provider = ProviderUrl(view_name='provider-detail', read_only=True)
    id = serializers.CharField(source='uuid', read_only=True)
    amount = serializers.DecimalField(required=False, decimal_places=2,
                                      max_digits=12, min_value=0)

    class Meta:
        model = Transaction
        fields = ('id', 'url', 'customer', 'provider', 'amount', 'currency',
                  'state', 'proforma', 'invoice', 'can_be_consumed',
                  'payment_processor', 'payment_method', 'pay_url',
                  'valid_until', 'updated_at', 'created_at', 'fail_code',
                  'refund_code', 'cancel_code')

        read_only_fields = ('customer', 'provider', 'can_be_consumed', 'pay_url',
                            'id', 'url', 'state', 'updated_at', 'created_at',
                            'payment_processor', 'fail_code', 'refund_code',
                            'cancel_code')
        updateable_fields = ('valid_until', 'success_url', 'failed_url')
        extra_kwargs = {'amount': {'required': False},
                        'currency': {'required': False},
                        'invoice': {'view_name': 'invoice-detail'},
                        'proforma': {'view_name': 'proforma-detail'}}

    def validate(self, attrs):
        attrs = super(TransactionSerializer, self).validate(attrs)

        if not attrs:
            return attrs

        if self.instance:
            if self.instance.state != Transaction.States.Initial:
                message = "The transaction cannot be modified once it is in {}"\
                          " state.".format(self.instance.state)
                raise serializers.ValidationError(message)

        return attrs
