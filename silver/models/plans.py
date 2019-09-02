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

from model_utils import Choices

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from silver.utils.international import currencies
from silver.utils.models import UnsavedForeignKey


class PlanManager(models.Manager):
    def get_queryset(self):
        return super(PlanManager, self).get_queryset().select_related('product_code')


@python_2_unicode_compatible
class Plan(models.Model):
    objects = PlanManager()

    class INTERVALS(object):
        DAY = 'day'
        WEEK = 'week'
        MONTH = 'month'
        YEAR = 'year'

    INTERVAL_CHOICES = Choices(
        (INTERVALS.DAY, _('Day')),
        (INTERVALS.WEEK, _('Week')),
        (INTERVALS.MONTH, _('Month')),
        (INTERVALS.YEAR, _('Year'))
    )

    name = models.CharField(
        max_length=200, help_text='Display name of the plan.',
        db_index=True
    )
    interval = models.CharField(
        choices=INTERVAL_CHOICES, max_length=12, default=INTERVALS.MONTH,
        help_text='The frequency with which a subscription should be billed.'
    )
    interval_count = models.PositiveIntegerField(
        help_text='The number of intervals between each subscription billing'
    )
    amount = models.DecimalField(
        max_digits=19, decimal_places=4, validators=[MinValueValidator(0.0)],
        help_text='The amount in the specified currency to be charged on the '
                  'interval specified.'
    )
    currency = models.CharField(
        choices=currencies, max_length=4, default='USD',
        help_text='The currency in which the subscription will be charged.'
    )
    trial_period_days = models.PositiveIntegerField(
        null=True, blank=True,
        help_text='Number of trial period days granted when subscribing a '
                  'customer to this plan.',
        verbose_name='Trial days'
    )
    generate_documents_on_trial_end = models.NullBooleanField(
        help_text="If this is set to True, then billing documents will be generated when the "
                  "subscription trial ends, instead of waiting for the end of the billing cycle."
    )
    separate_cycles_during_trial = models.NullBooleanField(
        help_text="If this is set to True, then the trial period cycle will be split if it spans "
                  "across multiple billing intervals."
    )
    prebill_plan = models.NullBooleanField(
        help_text="If this is set to True, then the plan base amount will be billed at the"
                  "beginning of the billing cycle rather than after the end."
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


@python_2_unicode_compatible
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
