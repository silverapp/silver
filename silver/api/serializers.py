from rest_framework import serializers

from silver.models import (MeteredFeatureUnitsLog, Customer, Subscription,
                           MeteredFeature, Plan, Provider)


class MeteredFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeteredFeature
        fields = ('name', 'price_per_unit', 'included_units')


class MeteredFeatureUnitsLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeteredFeatureUnitsLog
        fields = ('metered_feature', 'subscription', 'consumed_units',
                  'start_date', 'end_date')


class PlanSerializer(serializers.ModelSerializer):
    metered_features = MeteredFeatureSerializer(
        source='metered_features',
        many=True, read_only=True
    )
    url = serializers.HyperlinkedIdentityField(
        source='*', view_name='silver_api:plan-detail'
    )

    class Meta:
        model = Plan
        fields = ('name', 'url', 'interval', 'interval_count', 'amount',
                  'currency', 'trial_period_days', 'due_days', 'generate_after',
                  'enabled', 'private', 'product_code', 'metered_features')


class SubscriptionSerializer(serializers.ModelSerializer):
    trial_end = serializers.DateField(required=False)
    start_date = serializers.DateField(required=False)
    ended_at = serializers.DateField(read_only=True)
    plan = serializers.HyperlinkedRelatedField(
        source='plan',
        view_name='silver_api:plan-detail',
    )
    customer = serializers.HyperlinkedRelatedField(
        source='customer', view_name='silver_api:customer-detail',
    )
    url = serializers.HyperlinkedIdentityField(
        source='pk', view_name='silver_api:subscription-detail'
    )

    class Meta:
        model = Subscription
        fields = ('plan', 'customer', 'url', 'trial_end', 'start_date',
                  'ended_at', 'state')
        read_only_fields = ('state', )


class SubscriptionDetailSerializer(SubscriptionSerializer):
    metered_features = MeteredFeatureSerializer(
        source='plan.metered_features', many=True, read_only=True
    )

    class Meta:
        model = Subscription
        fields = ('plan', 'customer', 'url', 'trial_end', 'start_date',
                  'ended_at', 'state', 'metered_features')
        read_only_fields = ('state', )


class CustomerSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='silver_api:customer-detail')

    class Meta:
        model = Customer
        fields = ('id', 'url', 'customer_reference', 'name', 'company', 'email',
                  'address_1', 'address_2', 'city', 'state', 'zip_code',
                  'country', 'extra', 'sales_tax_name', 'sales_tax_percent')


class ProviderSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='silver_api:provider-detail')

    class Meta:
        model = Provider
        fields = ('id', 'url', 'name', 'company', 'email', 'address_1',
                  'address_2', 'city', 'state', 'zip_code', 'country', 'extra')
