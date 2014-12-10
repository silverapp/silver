from string import rfind
from rest_framework import serializers
from silver.models import (MeteredFeatureUnitsLog, Customer, Subscription,
                           MeteredFeature, Plan, Provider)
from rest_framework.reverse import reverse


class MeteredFeatureSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='silver_api:metered-feature-detail')

    class Meta:
        model = MeteredFeature
        fields = ('name', 'price_per_unit', 'included_units', 'url')


class MeteredFeatureLogRelatedField(serializers.HyperlinkedRelatedField):
    def get_url(self, obj, view_name, request, format):
        request = self.context['request']
        path = request._request.path
        left = '/subscriptions/'.__len__()
        right = rfind(path, '/', left)
        sub_pk = path[left:right]
        kwargs = {
            'sub': sub_pk,
            'mf': obj.pk
        }
        return reverse(view_name, kwargs=kwargs, request=request, format=format)


class MeteredFeatureRelatedField(serializers.HyperlinkedRelatedField):
    def get_url(self, obj, view_name, request, format):
        kwargs = {'pk': obj.pk}
        return reverse(view_name, kwargs=kwargs, request=request, format=format)

    def to_native(self, obj):
        request = self.context.get('request', None)
        return MeteredFeatureSerializer(obj, context={'request': request}).data


class MeteredFeatureInSubscriptionSerializer(serializers.ModelSerializer):
    units_log_url = MeteredFeatureLogRelatedField(
        view_name='silver_api:mf-log-list', source='*', read_only=True
    )

    class Meta:
        model = MeteredFeature
        fields = ('name', 'price_per_unit', 'included_units', 'units_log_url')


class MeteredFeatureUnitsLogSerializer(serializers.ModelSerializer):
    metered_feature = serializers.HyperlinkedRelatedField(
        view_name='silver_api:metered-feature-detail',
        read_only=True,
    )
    subscription = serializers.HyperlinkedRelatedField(
        view_name='silver_api:subscription-detail',
        read_only=True
    )
    # The 2 lines below are needed because of a DRF3 bug
    start_date = serializers.DateField(read_only=True)
    end_date = serializers.DateField(read_only=True)

    class Meta:
        model = MeteredFeatureUnitsLog
        fields = ('metered_feature', 'subscription', 'consumed_units',
                  'start_date', 'end_date')


class ProviderSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='silver_api:provider-detail')

    class Meta:
        model = Provider
        fields = ('id', 'url', 'name', 'company', 'email', 'address_1',
                  'address_2', 'city', 'state', 'zip_code', 'country', 'extra')


class PlanSerializer(serializers.ModelSerializer):
    metered_features = MeteredFeatureSerializer(
        required=False, many=True
    )

    url = serializers.HyperlinkedIdentityField(
        source='*', view_name='silver_api:plan-detail'
    )
    provider = serializers.HyperlinkedRelatedField(
        queryset=Provider.objects.all(),
        view_name='silver_api:provider-detail',
    )

    class Meta:
        model = Plan
        fields = ('name', 'url', 'interval', 'interval_count', 'amount',
                  'currency', 'trial_period_days', 'due_days', 'generate_after',
                  'enabled', 'private', 'product_code', 'metered_features',
                  'provider')

    def create(self, validated_data):
        metered_features_data = validated_data.pop('metered_features')
        metered_features = []
        for mf_data in metered_features_data:
            metered_features.append(MeteredFeature.objects.create(**mf_data))

        plan = Plan.objects.create(**validated_data)
        plan.metered_features.add(*metered_features)

        return plan

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.generate_after = validated_data.get('generate_after', instance.generate_after)
        instance.due_days = validated_data.get('due_days', instance.due_days)
        instance.save()

        return instance


class SubscriptionSerializer(serializers.ModelSerializer):
    trial_end = serializers.DateField(required=False)
    start_date = serializers.DateField(required=False)
    ended_at = serializers.DateField(read_only=True)
    plan = serializers.HyperlinkedRelatedField(
        queryset=Plan.objects.all(),
        view_name='silver_api:plan-detail',
    )
    customer = serializers.HyperlinkedRelatedField(
        view_name='silver_api:customer-detail',
        queryset=Customer.objects.all()
    )
    url = serializers.HyperlinkedIdentityField(
        source='pk', view_name='silver_api:subscription-detail'
    )

    def validate(self, attrs):
        instance = Subscription(**attrs)
        instance.clean()
        return attrs

    class Meta:
        model = Subscription
        fields = ('plan', 'customer', 'url', 'trial_end', 'start_date',
                  'ended_at', 'state')
        read_only_fields = ('state', )


class SubscriptionDetailSerializer(SubscriptionSerializer):
    metered_features = MeteredFeatureInSubscriptionSerializer(
        source='plan.metered_features', many=True, read_only=True
    )

    def validate(self, attrs):
        instance = Subscription(**attrs)
        instance.clean()
        return attrs

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
