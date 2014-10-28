from rest_framework import serializers
from silver.models import MeteredFeatureUnitsLog, Customer, BillingDetail


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
