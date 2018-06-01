from django.core.exceptions import ValidationError
from rest_framework import serializers

from silver.api.serializers.common import MeteredFeatureSerializer
from silver.api.serializers.product_codes_serializer import ProductCodeRelatedField
from silver.models import Provider, Plan, MeteredFeature


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
        except ValidationError as e:
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
