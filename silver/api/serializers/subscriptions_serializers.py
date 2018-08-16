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
from rest_framework.reverse import reverse

from silver.api.serializers.common import CustomerUrl, MeteredFeatureSerializer
from silver.api.serializers.plans_serializer import PlanSerializer
from silver.models import MeteredFeatureUnitsLog, Subscription, Customer


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


class SubscriptionUrl(serializers.HyperlinkedRelatedField):
    def get_url(self, obj, view_name, request, format):
        kwargs = {'customer_pk': obj.customer_id, 'subscription_pk': obj.pk}
        return reverse(view_name, kwargs=kwargs, request=request,
                       format=format)


class SubscriptionSerializer(serializers.HyperlinkedModelSerializer):
    trial_end = serializers.DateField(required=False)
    start_date = serializers.DateField(required=False)
    ended_at = serializers.DateField(read_only=True)
    url = SubscriptionUrl(view_name='subscription-detail', source='*',
                          queryset=Subscription.objects.all(), required=False)
    updateable_buckets = serializers.ReadOnlyField()
    meta = JSONField(required=False)

    class Meta:
        model = Subscription
        fields = ('id', 'url', 'plan', 'customer', 'trial_end', 'start_date', 'cancel_date',
                  'ended_at', 'state', 'reference', 'updateable_buckets', 'meta', 'description')
        read_only_fields = ('state', 'updateable_buckets')
        extra_kwargs = {'customer': {'lookup_url_kwarg': 'customer_pk'}}

    def validate(self, attrs):
        attrs = super(SubscriptionSerializer, self).validate(attrs)

        instance = Subscription(**attrs)
        instance.clean()
        return attrs


class SubscriptionDetailSerializer(SubscriptionSerializer):
    plan = PlanSerializer(read_only=True)

    class Meta(SubscriptionSerializer.Meta):
        fields = SubscriptionSerializer.Meta.fields + ('plan',)
