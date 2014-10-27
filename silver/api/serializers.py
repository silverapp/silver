from rest_framework import serializers
from silver.models import MeteredFeatureUnitsLog


class MeteredFeatureLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeteredFeatureUnitsLog
        fields = ('metered_feature', 'subscription', 'consumed_units',
                  'start_date', 'end_date'
        )
