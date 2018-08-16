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

from rest_framework import serializers
from rest_framework.fields import JSONField
from rest_framework.relations import HyperlinkedRelatedField

from silver.api.serializers.common import CustomerUrl
from silver.api.serializers.subscriptions_serializers import SubscriptionUrl
from silver.models import Provider, Customer


class ProviderSerializer(serializers.HyperlinkedModelSerializer):
    meta = JSONField(required=False)

    class Meta:
        model = Provider
        fields = ('id', 'url', 'name', 'company', 'invoice_series', 'flow',
                  'email', 'address_1', 'address_2', 'city', 'state',
                  'zip_code', 'country', 'extra', 'invoice_series',
                  'invoice_starting_number', 'proforma_series',
                  'proforma_starting_number', 'meta')

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
    meta = JSONField(required=False)
    url = CustomerUrl(view_name='customer-detail', read_only=True, source='*')

    class Meta:
        model = Customer
        fields = ('id', 'url', 'customer_reference', 'first_name', 'last_name',
                  'company', 'email', 'address_1', 'address_2', 'city',
                  'state', 'zip_code', 'country', 'currency', 'phone', 'extra',
                  'sales_tax_number', 'sales_tax_name', 'sales_tax_percent',
                  'consolidated_billing', 'subscriptions', 'payment_methods',
                  'transactions', 'meta')
