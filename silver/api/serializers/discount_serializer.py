from rest_framework.fields import SerializerMethodField
from rest_framework.relations import SlugRelatedField
from rest_framework.serializers import HyperlinkedModelSerializer

from silver.models import Discount
from silver.utils.serializers import AutoCleanSerializerMixin


class DiscountSerializer(AutoCleanSerializerMixin,
                         HyperlinkedModelSerializer):
    product_code = SlugRelatedField(
        slug_field='value',
        read_only=True
    )

    period_applied_to_subscription = SerializerMethodField()
    is_active_for_subscription = SerializerMethodField()

    class Meta:
        model = Discount
        fields = read_only_fields = [
            "id",
            "name",
            "product_code",
            "percentage",
            "applies_to",
            "document_entry_behavior",
            "discount_stacking_type",
            "state",
            "start_date",
            "end_date",
            "duration_count",
            "duration_interval",
            "period_applied_to_subscription",
            "is_active_for_subscription",
        ]

    def get_period_applied_to_subscription(self, discount):
        subscription = self.context.get("subscription")

        if not subscription:
            return None

        return discount.period_applied_to_subscription(subscription)

    def get_is_active_for_subscription(self, discount):
        subscription = self.context.get("subscription")

        if not subscription:
            return None

        return discount.is_active_for_subscription(subscription)
