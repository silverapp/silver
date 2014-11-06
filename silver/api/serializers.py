from rest_framework import serializers
from silver.models import MeteredFeatureUnitsLog, Customer, BillingDetail, \
    Subscription, MeteredFeature, Plan


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan


class SubscriptionSerializer(serializers.ModelSerializer):
    trial_end = serializers.DateField(required=False)
    start_date = serializers.DateField(required=False)
    ended_at = serializers.DateField(read_only=True)
    plan = serializers.HyperlinkedRelatedField(
        source='plan',
        view_name='silver_api:plan-detail',
    )
    customer = serializers.HyperlinkedRelatedField(
        source='customer',
        view_name='silver_api:customer-detail',
    )

    class Meta:
        model = Subscription
        fields = ('plan', 'customer', 'trial_end', 'start_date', 'ended_at',
                  'state')
        read_only_fields = ('state', )


class MeteredFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeteredFeature


class SubscriptionDetailSerializer(SubscriptionSerializer):
    metered_features = MeteredFeatureSerializer(source='plan.metered_features',
                                                many=True, read_only=True)

    class Meta:
        model = Subscription
        fields = ('plan', 'customer', 'trial_end', 'start_date', 'ended_at',
                  'state', 'metered_features')
        read_only_fields = ('state', )


class MeteredFeatureUnitsLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeteredFeatureUnitsLog
        fields = ('metered_feature', 'subscription', 'consumed_units',
                  'start_date', 'end_date')


class BillingDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillingDetail
        fields = ('name', 'company', 'email', 'address_1', 'address_2',
                  'country', 'city', 'state', 'zip_code', 'extra')


class CustomerSerializer(serializers.ModelSerializer):
    billing_details = BillingDetailSerializer(source='billing_details')

    class Meta:
        model = Customer
        fields = ('customer_reference', 'billing_details', 'sales_tax_percent',
                  'sales_tax_name')
        depth = 1
