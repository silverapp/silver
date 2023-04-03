from datetime import datetime
from fractions import Fraction
from typing import Tuple

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q, F
from django.utils import timezone

from silver.models import Subscription
from silver.models.documents.entries import OriginType
from silver.utils.dates import end_of_interval
from silver.utils.models import AutoCleanModelMixin


class BonusState(models.TextChoices):
    ACTIVE = "active", "Active"
    INACTIVE = "inactive", "Inactive"


class DurationIntervals(models.TextChoices):
    BILLING_CYCLE = 'billing_cycle'
    DAY = 'day'
    WEEK = 'week'
    MONTH = 'month'
    YEAR = 'year'


class BonusTarget(models.TextChoices):
    METERED_FEATURES_UNITS = "metered_features_units"


class DocumentEntryBehavior(models.TextChoices):
    APPLY_DIRECTLY_TO_TARGET_ENTRIES = "apply_directly_to_target", "Apply directly to target entries"
    APPLY_AS_SEPARATE_ENTRY_PER_ENTRY = "apply_separately_per_entry", "Apply as separate entry, per entry"


class Bonus(AutoCleanModelMixin, models.Model):
    STATES = BonusState
    TARGET = BonusTarget
    DURATION_INTERVALS = DurationIntervals
    ENTRY_BEHAVIOR = DocumentEntryBehavior

    name = models.CharField(
        max_length=200,
        help_text='The bonus\'s name. May be used for identification or displaying in an invoice.',
    )
    product_code = models.ForeignKey('ProductCode', null=True, blank=True,
                                     related_name='bonuses', on_delete=models.PROTECT,
                                     help_text="The bonus's product code.")

    filter_customers = models.ManyToManyField("silver.Customer", related_name='filtering_bonuses', blank=True)
    filter_subscriptions = models.ManyToManyField("silver.Subscription", related_name='filtering_bonuses', blank=True)
    filter_plans = models.ManyToManyField("silver.Plan", related_name='filtering_bonuses', blank=True)
    filter_product_codes = models.ManyToManyField("silver.ProductCode", related_name="filtering_bonuses", blank=True)
    filter_annotations = models.JSONField(default=list, blank=True)

    amount = models.DecimalField(
        max_digits=19, decimal_places=4, validators=[MinValueValidator(0.0)], null=True, blank=True,
        help_text='The bonus amount. For example this might refer to the metered features included units.'
    )
    amount_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="The bonus amount as percentage. For example 25 (%)"
    )

    applies_to = models.CharField(choices=TARGET.choices, max_length=24,
                                  help_text="Defines what the bonus applies to.",
                                  default=TARGET.METERED_FEATURES_UNITS)

    document_entry_behavior = models.CharField(choices=ENTRY_BEHAVIOR.choices,
                                               max_length=32, default=ENTRY_BEHAVIOR.APPLY_AS_SEPARATE_ENTRY_PER_ENTRY,
                                               help_text="Defines how the discount will be shown in the billing "
                                                         "documents.")

    state = models.CharField(choices=STATES.choices, max_length=16, default=STATES.ACTIVE,
                             help_text="Can be used to easily toggle bonuses on or off.")

    start_date = models.DateField(null=True, blank=True,
                                  help_text="When set, the bonus will only apply to entries with a lower "
                                            "or equal start_date. Otherwise, a prorated bonus may still apply, but"
                                            "only if the entries end_date is greater than the bonus's start_date.")
    end_date = models.DateField(null=True, blank=True,
                                help_text="When set, the bonus will only apply to entries with a greater "
                                          "or equal end_date. Otherwise, a prorated bonus may still apply, but"
                                          "only if the entries start_date is lower than the bonus's end_date.")

    duration_count = models.IntegerField(null=True, blank=True,
                                         help_text="Indicate the duration for which the bonus is available, after "
                                                   "a subscription started. If not set, the duration is indefinite.")
    duration_interval = models.CharField(null=True, blank=True, max_length=16, choices=DURATION_INTERVALS.choices)

    class Meta:
        verbose_name_plural = "bonuses"

    def clean(self):
        if not self.amount and not self.amount_percentage:
            raise ValidationError("Bonuses must have one of `amount` or `amount_percentage` specified.")
        elif self.amount and self.amount_percentage:
            raise ValidationError("Bonuses cannot have both `amount` and `amount_percentage` specified.")

    def period_applied_to_subscription(self, subscription):
        start_date = subscription.start_date
        end_date = subscription.ended_at

        if not start_date:
            return None

        if self.duration_count and self.duration_interval:
            interval = (subscription.plan.interval if self.duration_interval == DurationIntervals.BILLING_CYCLE
                        else self.duration_interval)

            duration_end_date = end_of_interval(subscription.start_date, interval, self.duration_count)
            if not end_date:
                end_date = duration_end_date

            if duration_end_date < end_date:
                end_date = duration_end_date

        if self.start_date and self.start_date > start_date:
            start_date = self.start_date

        if end_date and self.end_date and self.end_date < end_date:
            end_date = self.end_date

        return {
            "start_date": start_date,
            "end_date": end_date
        }

    @classmethod
    def for_subscription(cls, subscription: "silver.models.Subscription"):
        return Bonus.objects.filter(
            Q(filter_customers=subscription.customer) | Q(filter_customers=None),
            Q(filter_subscriptions=subscription) | Q(filter_subscriptions=None),
            Q(filter_plans=subscription.plan) | Q(filter_plans=None),
            Q(filter_product_codes=subscription.plan.product_code) | Q(filter_product_codes=None),
        ).annotate(_filtered_product_codes=F("filter_product_codes"))

    def is_active_for_subscription(self, subscription):
        if not subscription.state == subscription.STATES.ACTIVE:
            return False

        if not self.state == self.STATES.ACTIVE:
            return False

        period = self.period_applied_to_subscription(subscription)
        start_date, end_date = period["start_date"], period["end_date"]

        return (start_date or datetime.min.date()) <= timezone.now().date() <= (end_date or datetime.max.date())

    def extra_proration_fraction(
        self, subscription, start_date, end_date, entry_type: OriginType
    ) -> Tuple[Fraction, bool]:
        entry_start_date = start_date
        entry_end_date = end_date

        if subscription.on_trial(end_date):
            return Fraction(0), True

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

        status, fraction = subscription._get_proration_status_and_fraction(start_date, end_date, entry_type)

        if self.amount_percentage:
            if entry_start_date == start_date and entry_end_date == end_date:
                return Fraction(1), False

            already_prorated, entry_proration_fraction = subscription._get_proration_status_and_fraction(
                entry_start_date, entry_end_date, entry_type
            )

            if already_prorated:
                fraction /= entry_proration_fraction

        return fraction, status

    def matching_subscriptions(self):
        subscriptions = self.filter_subscriptions.all()
        if not subscriptions:
            subscriptions = Subscription.objects.all()

        customers = self.filter_customers.all()
        plans = self.filter_plans.all()
        product_codes = self.filter_product_codes.all()

        if customers:
            subscriptions = subscriptions.filter(customer__in=customers)

        if plans:
            subscriptions = subscriptions.filter(plan__in=plans)

        if product_codes:
            subscriptions = subscriptions.filter(
                Q(plan__product_code__in=product_codes) |
                Q(plan__metered_features__product_code__in=product_codes)
            )

        return subscriptions

    def matches_metered_feature_units(self, metered_feature, annotations) -> bool:
        if hasattr(self, "_filtered_product_codes"):
            if self._filtered_product_codes and metered_feature.product_code not in self._filtered_product_codes:
                return False

        if self.filter_annotations:
            if not set(self.filter_annotations).intersection(set(annotations)):
                return False

        return True

    @property
    def amount_description(self) -> str:
        bonus = []
        amount = self.amount or f"{self.amount_percentage}%"

        if self.applies_to in [self.TARGET.METERED_FEATURES_UNITS]:
            bonus.append(f"{amount} off Metered Features")

        return ", ".join(bonus)

    def __str__(self) -> str:
        return self.name
