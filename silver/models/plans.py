# Copyright (c) 2016 Presslabs SRL
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

from __future__ import absolute_import, unicode_literals

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from silver.utils.dates import INTERVALS as DATE_INTERVALS
from silver.utils.international import currencies
from silver.utils.models import UnsavedForeignKey


class PlanManager(models.Manager):
    def get_queryset(self):
        return super(PlanManager, self).get_queryset().select_related('product_code')


class IntervalChoices(models.TextChoices):
    DAY = DATE_INTERVALS.DAY, _('Day')
    WEEK = DATE_INTERVALS.WEEK, _('Week')
    MONTH = DATE_INTERVALS.MONTH, _('Month')
    YEAR = DATE_INTERVALS.YEAR, _('Year')


class SeparateEntriesByIntervalChoices(models.TextChoices):
    DISABLED = 'disabled', _('Disabled')
    INHERIT = 'inherit', _('Inherit')


class Plan(models.Model):
    objects = PlanManager()

    INTERVALS = IntervalChoices
    SEPARATE_ENTRIES_BY_INTERVAL = SeparateEntriesByIntervalChoices

    name = models.CharField(
        max_length=200, help_text='Display name of the plan.',
        db_index=True
    )
    interval = models.CharField(
        choices=INTERVALS.choices, max_length=12, default=INTERVALS.MONTH,
        help_text='The frequency with which a subscription should be billed.'
    )
    interval_count = models.PositiveIntegerField(
        help_text='The number of intervals between each subscription billing.'
    )

    alternative_metered_features_interval = models.CharField(
        null=True, blank=True, choices=INTERVALS.choices, max_length=12,
        help_text='Optional frequency with which a subscription\'s metered features should be billed.'
    )
    alternative_metered_features_interval_count = models.PositiveIntegerField(
        null=True, blank=True,
        help_text='Optional number of intervals between each subscription\'s metered feature billing.'
    )

    amount = models.DecimalField(
        max_digits=19, decimal_places=4, validators=[MinValueValidator(0.0)],
        help_text='The amount in the specified currency to be charged on the interval specified.'
    )
    currency = models.CharField(
        choices=currencies, max_length=4, default='USD',
        help_text='The currency in which the subscription will be charged.'
    )
    trial_period_days = models.PositiveIntegerField(
        null=True, blank=True,
        help_text='Number of trial period days granted when subscribing a customer to this plan.',
        verbose_name='Trial days'
    )
    generate_documents_on_trial_end = models.BooleanField(
        null=True,
        help_text="If this is set to True, then billing documents will be generated when the "
                  "subscription trial ends, instead of waiting for the end of the billing cycle."
    )
    separate_cycles_during_trial = models.BooleanField(
        null=True,
        help_text="If this is set to True, then the trial period cycle will be split if it spans "
                  "across multiple billing intervals."
    )
    separate_plan_entries_per_base_interval = models.CharField(
        choices=SEPARATE_ENTRIES_BY_INTERVAL.choices, default=SEPARATE_ENTRIES_BY_INTERVAL.INHERIT,
        max_length=16,
        help_text="If not disabled, this will cause the plan entries to be separated by the base interval. "
                  "For example a plan with interval=month, interval_count=3, will cause the entries to be split "
                  "by each month, resulting in 3 entries with "
    )
    prebill_plan = models.BooleanField(
        null=True,
        help_text="If this is set to True, then the plan base amount will be billed at the "
                  "beginning of the billing cycle rather than after the end."
    )
    only_bill_metered_features_with_base_amount = models.BooleanField(
        default=False,
        help_text="When set to True, Metered Features will only be billed when the base plan's amount "
                  "is billed. For example, for a plan with interval=month, interval_count=3, metered "
                  "features will only be billed every 3 months, along with the base amount."
    )

    metered_features = models.ManyToManyField(
        'MeteredFeature', blank=True,
        help_text="A list of the plan's metered features."
    )
    generate_after = models.PositiveIntegerField(
        default=0,
        help_text='Number of seconds to wait after current billing cycle ends '
                  'before generating the invoice. This can be used to allow '
                  'systems to finish updating feature counters.'
    )
    cycle_billing_duration = models.DurationField(
        null=True, blank=True,
        help_text="This can be used to ensure that the billing date doesn't pass a certain date.\n"
                  "For example if this field is set to 2 days, for a monthly subscription, the "
                  "billing date will never surpass the 2nd day of the month. Billing documents can "
                  "still be generated after that day during the billing cycle, but their billing "
                  "date will appear to be the end of the cycle billing duration."
    )
    enabled = models.BooleanField(default=True,
                                  help_text='Whether to accept subscriptions.')
    private = models.BooleanField(default=False,
                                  help_text='Indicates if a plan is private.')
    product_code = models.ForeignKey(
        'ProductCode', help_text='The product code for this plan.', on_delete=models.PROTECT
    )
    provider = models.ForeignKey(
        'Provider', related_name='plans',
        help_text='The provider which provides the plan.', on_delete=models.CASCADE
    )

    class Meta:
        ordering = ('name',)

    @staticmethod
    def validate_metered_features(metered_features):
        product_codes = dict()
        for mf in metered_features:
            if product_codes.get(mf.product_code.value, None):
                err_msg = 'A plan cannot have two or more metered features ' \
                          'with the same product code. (%s, %s)' \
                          % (mf.name, product_codes.get(mf.product_code.value))
                raise ValidationError(err_msg)
            product_codes[mf.product_code.value] = mf.name

    def __str__(self):
        return "%s (%s)" % (self.name, self.provider.name)

    @property
    def provider_flow(self):
        return self.provider.flow

    @property
    def base_interval(self):
        return self.interval

    @property
    def metered_features_interval(self):
        return self.alternative_metered_features_interval or self.interval

    @property
    def base_interval_count(self):
        return self.interval_count

    @property
    def metered_features_interval_count(self):
        return self.alternative_metered_features_interval_count or self.interval_count


class MeteredFeature(models.Model):
    name = models.CharField(
        max_length=200,
        help_text='The feature display name.',
        db_index=True,
    )
    unit = models.CharField(max_length=20)
    price_per_unit = models.DecimalField(
        max_digits=19, decimal_places=4, validators=[MinValueValidator(0.0)],
        help_text='The price per unit.',
    )
    included_units = models.DecimalField(
        max_digits=19, decimal_places=4, validators=[MinValueValidator(0.0)],
        help_text='The number of included units per plan interval.'
    )
    included_units_during_trial = models.DecimalField(
        max_digits=19, decimal_places=4, validators=[MinValueValidator(0.0)],
        blank=True, null=True,
        help_text='The number of included units during the trial period.'
    )
    product_code = UnsavedForeignKey(
        'ProductCode', help_text='The product code for this plan.', on_delete=models.PROTECT,
    )

    class Meta:
        ordering = ('name',)

    def __str__(self):
        fmt = u'{name} ({price:.2f}$, {included:.2f} included)'
        return fmt.format(name=self.name, price=self.price_per_unit,
                          included=self.included_units)
