# Copyright (c) 2022 Pressinfra SRL
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

from decimal import Decimal
from fractions import Fraction
from typing import List, Iterable, Tuple

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, F
from django.template.loader import render_to_string

from .subscriptions import Subscription
from .documents.entries import OriginType
from .fields import field_template_path
from silver.utils.dates import end_of_interval
from silver.utils.models import AutoCleanModelMixin


class DocumentEntryBehavior(models.TextChoices):
    DEFAULT = "default", "Default"
    # FORCE_PER_ENTRY = "force_per_entry", "Force per entry"
    # FORCE_PER_ENTRY_TYPE = "force_per_entry", "Force per entry type"
    FORCE_PER_DOCUMENT = "force_per_document", "Force per document"


class DiscountStackingType(models.TextChoices):
    # SUCCESSIVE = "successive", "Successive"
    ADDITIVE = "additive", "Additive"
    NONCUMULATIVE = "noncumulative", "Noncumulative"


class DiscountState(models.TextChoices):
    ACTIVE = "active", "Active"
    INACTIVE = "inactive", "Inactive"


class DiscountTarget(models.TextChoices):
    ALL = "all"
    PLAN_AMOUNT = "plan_amount"
    METERED_FEATURES = "metered_features"


class DurationIntervals(models.TextChoices):
    BILLING_CYCLE = 'billing_cycle'
    DAY = 'day'
    WEEK = 'week'
    MONTH = 'month'
    YEAR = 'year'


class Discount(AutoCleanModelMixin, models.Model):
    STATES = DiscountState
    STACKING_TYPES = DiscountStackingType
    ENTRY_BEHAVIOR = DocumentEntryBehavior
    TARGET = DiscountTarget
    DURATION_INTERVALS = DurationIntervals

    name = models.CharField(
        max_length=200,
        help_text='The discount\'s name. May be used for identification or displaying in an invoice.',
    )
    product_code = models.ForeignKey('ProductCode', null=True, blank=True,
                                     related_name='discounts', on_delete=models.PROTECT,
                                     help_text="The discount's product code.")

    customers = models.ManyToManyField("silver.Customer", related_name='discounts', blank=True)
    subscriptions = models.ManyToManyField("silver.Subscription", related_name='discounts', blank=True)
    plans = models.ManyToManyField("silver.Plan", related_name='discounts', blank=True)

    percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
                                     help_text="A percentage to be discounted. For example 25 (%)")
    applies_to = models.CharField(choices=TARGET.choices, max_length=24,
                                  help_text="Defines what the discount applies to.",
                                  default=TARGET.ALL)

    document_entry_behavior = models.CharField(choices=ENTRY_BEHAVIOR.choices,
                                               max_length=32, default=ENTRY_BEHAVIOR.DEFAULT,
                                               help_text="Defines how the discount will be shown in the billing "
                                                         "documents.")

    discount_stacking_type = models.CharField(choices=STACKING_TYPES.choices,
                                              max_length=24, default=STACKING_TYPES.ADDITIVE,
                                              help_text="Defines how the discount will interact with other discounts.")

    state = models.CharField(choices=STATES.choices, max_length=16, default=STATES.ACTIVE,
                             help_text="Can be used to easily toggle discounts on or off.")

    start_date = models.DateField(null=True, blank=True,
                                  help_text="When set, the discount will only apply to entries with a lower "
                                            "or equal start_date. Otherwise, a prorated discount may still apply, but"
                                            "only if the entries end_date is greater than the discount's start_date.")
    end_date = models.DateField(null=True, blank=True,
                                help_text="When set, the discount will only apply to entries with a greater "
                                          "or equal end_date. Otherwise, a prorated discount may still apply, but"
                                          "only if the entries start_date is lower than the discount's end_date.")

    duration_count = models.IntegerField(null=True, blank=True,
                                         help_text="Indicate the duration for which the discount is available, after "
                                                   "a subscription started. If not set, the duration is indefinite.")
    duration_interval = models.CharField(null=True, blank=True, max_length=16, choices=DURATION_INTERVALS.choices)

    def clean(self):
        if (
                self.percentage and
                not Decimal(0) <= self.percentage <= Decimal(100)
        ):
            raise ValidationError({"percentage": "Must be between 0 and 100."})

        if (
                self.percentage and
                not Decimal(0) <= self.percentage <= Decimal(100)
        ):
            raise ValidationError({"percentage": "Must be between 0 and 100."})

    #     if (
    #             self.document_entry_behavior == DocumentEntryBehavior.FORCE_PER_ENTRY and
    #             self.discount_stacking_type == DiscountStackingType.SUCCESSIVE
    #     ):
    #         raise ValidationError(
    #             {NON_FIELD_ERRORS: "Per entry Discounts cannot stack successively."}
    #         )

    def __str__(self) -> str:
        return self.name

    @property
    def amount_description(self) -> str:
        discount = []
        if self.applies_to in [self.TARGET.ALL, self.TARGET.PLAN_AMOUNT]:
            discount.append(f"{self.percentage}% off Plan")

        if self.applies_to in [self.TARGET.ALL, self.TARGET.METERED_FEATURES]:
            discount.append(f"{self.percentage}% off Metered Features")

        return ", ".join(discount)

    def matching_subscriptions(self):
        subscriptions = self.subscriptions.all()
        if not subscriptions:
            subscriptions = Subscription.objects.all()

        customers = self.customers.all()
        plans = self.plans.all()
        if customers:
            subscriptions = subscriptions.filter(customer__in=customers)

        if plans:
            subscriptions = subscriptions.filter(plan__in=plans)

        return subscriptions

    @classmethod
    def for_subscription(cls, subscription: "silver.models.Subscription"):
        return Discount.objects.filter(
            Q(customers=subscription.customer) | Q(customers=None),
            Q(subscriptions=subscription) | Q(subscriptions=None),
            Q(plans=subscription.plan) | Q(plans=None),
        ).annotate(matched_subscriptions=F("subscriptions"))

    # @classmethod
    # def for_subscription_per_entry(cls, subscription: "silver.models.Subscription"):
    #     return cls.for_subscription(subscription).filter(
    #         document_entry_behavior=DocumentEntryBehavior.FORCE_PER_ENTRY
    #     )

    # @classmethod
    # def for_subscription_per_entry_type(cls, subscription: "silver.models.Subscription"):
    #     return cls.for_subscription(subscription).filter(
    #         (
    #                 Q(document_entry_behavior=DocumentEntryBehavior.DEFAULT) &
    #                 ~Q(plan_amount_discount=F("percentage"))
    #         ) |
    #         Q(
    #             document_entry_behavior=DocumentEntryBehavior.FORCE_PER_ENTRY_TYPE
    #         )
    #     )

    @classmethod
    def for_subscription_per_document(cls, subscription: "silver.models.Subscription"):
        return cls.for_subscription(subscription).filter(
            (
                Q(document_entry_behavior=DocumentEntryBehavior.DEFAULT) &
                Q(plan_amount_discount=F("percentage"))
            ) |
            Q(
                document_entry_behavior=DocumentEntryBehavior.FORCE_PER_DOCUMENT
            )
        )

    @property
    def as_additive(self) -> Decimal:
        return (self.percentage or Decimal(0)) / Decimal(100)

    @property
    def as_multiplier(self) -> Decimal:
        return (Decimal(100) - self.percentage or 0) / Decimal(100)

    @classmethod
    def filter_discounts_affecting_plan(cls, discounts: Iterable["Discount"]) -> List["Discount"]:
        return [discount for discount in discounts
                if (
                    discount.percentage > 0 and
                    discount.applies_to in [DiscountTarget.ALL, DiscountTarget.PLAN_AMOUNT]
                )]

    @classmethod
    def filter_discounts_affecting_metered_features(cls, discounts: Iterable["Discount"]) -> List["Discount"]:
        return [discount for discount in discounts
                if (
                    discount.percentage > 0 and
                    discount.applies_to in [DiscountTarget.ALL, DiscountTarget.METERED_FEATURES]
                )]

    # @classmethod
    # def filter_discounts_per_entry(cls, discounts: Iterable["Discount"]) -> List["Discount"]:
    #     return [discount for discount in discounts
    #             if discount.document_entry_behavior == DocumentEntryBehavior.FORCE_PER_ENTRY]

    # @classmethod
    # def filter_discounts_per_entry_type(cls, discounts: Iterable["Discount"]) -> List["Discount"]:
    #     return [discount for discount in discounts
    #             if discount.document_entry_behavior == DocumentEntryBehavior.FORCE_PER_ENTRY_TYPE or
    #             (
    #                     discount.document_entry_behavior == DocumentEntryBehavior.DEFAULT and
    #                     discount.percentage != discount.percentage
    #             )]

    @classmethod
    def filter_discounts_per_document(cls, discounts: Iterable["Discount"]) -> List["Discount"]:
        return [discount for discount in discounts
                if discount.document_entry_behavior == DocumentEntryBehavior.FORCE_PER_DOCUMENT or
                (
                    discount.document_entry_behavior == DocumentEntryBehavior.DEFAULT and
                    discount.percentage == discount.percentage
                )]

    @classmethod
    def filter_additive(cls, discounts: Iterable["Discount"]) -> List["Discount"]:
        return [discount for discount in discounts
                if discount.discount_stacking_type == DiscountStackingType.ADDITIVE]

    # @classmethod
    # def filter_successive(cls, discounts: Iterable["Discount"]) -> List["Discount"]:
    #     return [discount for discount in discounts
    #             if discount.discount_stacking_type == DiscountStackingType.SUCCESSIVE]

    @classmethod
    def filter_noncumulative(cls, discounts: Iterable["Discount"]) -> List["Discount"]:
        return [discount for discount in discounts
                if discount.discount_stacking_type == DiscountStackingType.NONCUMULATIVE]

    def proration_fraction(self, subscription, start_date, end_date, entry_type: OriginType) -> Tuple[Fraction, bool]:
        if self.start_date and start_date < self.start_date:
            start_date = self.start_date

        if self.end_date and end_date > self.end_date:
            end_date = self.end_date

        if self.duration_count and self.duration_interval:
            interval = (subscription.plan.interval if self.duration_interval == DurationIntervals.BILLING_CYCLE
                        else self.duration_interval)

            duration_end_date = end_of_interval(subscription.start_date, interval, self.duration_count)
            if end_date > duration_end_date:
                end_date = duration_end_date

        sub_csd = subscription._cycle_start_date(ignore_trial=True, granulate=False, reference_date=start_date)
        sub_ced = subscription._cycle_start_date(ignore_trial=True, granulate=False, reference_date=end_date)

        if sub_csd <= start_date and sub_ced >= end_date:
            return Fraction(1), False

        status, fraction = subscription._get_proration_status_and_fraction(start_date, end_date, entry_type)

        return fraction, status

    def _entry_description(self, provider, customer, extra_context=None):
        context = {
            'name': self.name,
            'unit': 1,
            'product_code': self.product_code,
            'context': 'discount',
            'provider': provider,
            'customer': customer,
            'discount': self
        }

        if extra_context:
            context.update(extra_context)

        description_template_path = field_template_path(
            field='entry_description', provider=provider.slug
        )
        return render_to_string(description_template_path, context)
