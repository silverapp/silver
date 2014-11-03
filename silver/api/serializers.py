from rest_framework import serializers
from silver.models import MeteredFeatureUnitsLog, Customer, BillingDetail, \
    Subscription


class SubscriptionSerializer(serializers.ModelSerializer):
    trial_end = serializers.DateField()
    start_date = serializers.DateField()
    ended_at = serializers.DateField()
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
