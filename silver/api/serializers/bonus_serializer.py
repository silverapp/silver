from rest_framework.fields import SerializerMethodField
from rest_framework.relations import SlugRelatedField
from rest_framework.serializers import HyperlinkedModelSerializer

from silver.models import Bonus
from silver.utils.serializers import AutoCleanSerializerMixin


class BonusSerializer(AutoCleanSerializerMixin,
                      HyperlinkedModelSerializer):
    product_code = SlugRelatedField(
        slug_field='value',
        read_only=True
    )

    period_applied_to_subscription = SerializerMethodField()
    is_active_for_subscription = SerializerMethodField()

    class Meta:
        model = Bonus
        fields = read_only_fields = [
            "id",
            "name",
            "product_code",
            "amount",
            "amount_percentage",
            "applies_to",
            "state",
            "start_date",
            "end_date",
            "duration_count",
            "duration_interval",
            "period_applied_to_subscription",
            "is_active_for_subscription",
        ]

    def get_period_applied_to_subscription(self, bonus):
        subscription = self.context.get("subscription")

        if not subscription:
            return None

        return bonus.period_applied_to_subscription(subscription)

    def get_is_active_for_subscription(self, bonus):
        subscription = self.context.get("subscription")

        if not subscription:
            return None

        return bonus.is_active_for_subscription(subscription)
