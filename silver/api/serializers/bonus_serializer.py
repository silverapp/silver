# Copyright (c) 2024 Pressinfra SRL
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

from django.db.models import Q
from rest_framework.fields import SerializerMethodField
from rest_framework.relations import SlugRelatedField
from rest_framework.reverse import reverse
from rest_framework.serializers import HyperlinkedModelSerializer

from silver.models import Bonus
from silver.utils.serializers import AutoCleanSerializerMixin


class CustomerBonusSerializer(AutoCleanSerializerMixin,
                              HyperlinkedModelSerializer):
    product_code = SlugRelatedField(
        slug_field='value',
        read_only=True
    )

    only_for_subscriptions = SerializerMethodField()
    only_for_plans = SerializerMethodField()

    class Meta:
        model = Bonus
        fields = read_only_fields = [
            "id",
            "name",
            "product_code",
            "amount",
            "amount_percentage",
            "applies_to",
            "enabled",
            "start_date",
            "end_date",
            "duration_count",
            "duration_interval",
            "only_for_subscriptions",
            "only_for_plans",
        ]

    def get_only_for_subscriptions(self, bonus):
        customer_id = self.context["view"].kwargs["customer_pk"]

        return [
            reverse("subscription-detail",
                    kwargs={'customer_pk': customer_id, "subscription_pk": subscription.pk},
                    request=self.context["request"])
            for subscription in bonus.filter_subscriptions.filter(customer_id=customer_id)
        ]

    def get_only_for_plans(self, bonus):
        customer_id = self.context["view"].kwargs["customer_pk"]

        return [
            reverse("plan-detail", args=[plan.pk], request=self.context["request"])
            for plan in bonus.filter_plans.filter(
                Q(private=False) | Q(subscription__customer_id=customer_id)
            ).distinct()
        ]


class SubscriptionBonusSerializer(AutoCleanSerializerMixin,
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
            "enabled",
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
