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

import logging
from dataclasses import dataclass

from datetime import datetime, timedelta, date
from decimal import Decimal
from django.apps import apps
from fractions import Fraction
from functools import reduce
from typing import Tuple, List

from annoying.functions import get_object_or_None
from dateutil import rrule
from dateutil.relativedelta import relativedelta
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import JSONField
from django_fsm import FSMField, transition, TransitionNotAllowed
from model_utils import Choices

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.timezone import utc
from django.utils.translation import gettext_lazy as _

from silver.models import Plan
from silver.models.documents.entries import OriginType
from silver.models.billing_entities import Customer
from silver.models.documents import DocumentEntry
from silver.models.fields import field_template_path
from silver.utils.dates import ONE_DAY, first_day_of_month, first_day_of_interval, end_of_interval, monthdiff, \
    monthdiff_as_fraction
from silver.utils.numbers import quantize_fraction
from silver.validators import validate_reference


logger = logging.getLogger(__name__)


class MeteredFeatureUnitsLog(models.Model):
    metered_feature = models.ForeignKey('MeteredFeature', related_name='consumed',
                                        on_delete=models.CASCADE)
    subscription = models.ForeignKey('Subscription', related_name='mf_log_entries',
                                     on_delete=models.CASCADE)
    consumed_units = models.DecimalField(max_digits=19, decimal_places=4,
                                         validators=[MinValueValidator(0.0)])
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()

    annotation = models.CharField(max_length=256, null=True, blank=True)

    class Meta:
        unique_together = ('metered_feature', 'subscription', 'start_datetime', 'end_datetime',
                           'annotation')

    def clean(self):
        super(MeteredFeatureUnitsLog, self).clean()
        if self.subscription.state in [Subscription.STATES.ENDED,
                                       Subscription.STATES.INACTIVE]:
            if not self.id:
                action_type = "create"
            else:
                action_type = "change"
            err_msg = 'You cannot %s a metered feature units log belonging to '\
                      'an %s subscription.' % (action_type,
                                               self.subscription.state)
            raise ValidationError(err_msg)

        if not self.id:
            start_datetime = self.subscription.bucket_start_datetime(origin_type=OriginType.MeteredFeature)
            end_datetime = self.subscription.bucket_end_datetime(origin_type=OriginType.MeteredFeature)
            if get_object_or_None(MeteredFeatureUnitsLog, start_datetime=start_datetime,
                                  end_datetime=end_datetime,
                                  metered_feature=self.metered_feature,
                                  subscription=self.subscription):
                err_msg = 'A %s units log for the current date already exists.'\
                          ' You can edit that one.' % self.metered_feature
                raise ValidationError(err_msg)

    def save(self, *args, **kwargs):
        if self.annotation == "":
            self.annotation = None

        if not self.id:
            if not self.start_datetime:
                self.start_datetime = self.subscription.bucket_start_datetime(origin_type=OriginType.MeteredFeature)
            if not self.end_datetime:
                self.end_datetime = self.subscription.bucket_end_datetime(origin_type=OriginType.MeteredFeature)
            super(MeteredFeatureUnitsLog, self).save(*args, **kwargs)

        else:
            update_fields = []
            for field in self._meta.fields:
                if field.name != 'metered_feature' and field.name != 'id':
                    update_fields.append(field.name)
            kwargs['update_fields'] = kwargs.get('update_fields', update_fields)

            super(MeteredFeatureUnitsLog, self).save(*args, **kwargs)

    def __str__(self):
        return self.metered_feature.name


@dataclass
class OverageInfo:
    extra_consumed_units: Decimal
    annotations: List[str]
    directly_applied_bonuses: List["silver.models.Bonus"]
    separately_applied_bonuses: List["silver.models.Bonus"]


class Subscription(models.Model):
    class STATES(object):
        ACTIVE = 'active'
        INACTIVE = 'inactive'
        CANCELED = 'canceled'
        ENDED = 'ended'

    STATE_CHOICES = Choices(
        (STATES.ACTIVE, _('Active')),
        (STATES.INACTIVE, _('Inactive')),
        (STATES.CANCELED, _('Canceled')),
        (STATES.ENDED, _('Ended'))
    )

    class CANCEL_OPTIONS(object):
        NOW = 'now'
        END_OF_BILLING_CYCLE = 'end_of_billing_cycle'

    _INTERVALS_CODES = {
        'year': rrule.YEARLY,
        'month': rrule.MONTHLY,
        'week': rrule.WEEKLY,
        'day': rrule.DAILY
    }

    plan = models.ForeignKey(
        'Plan', on_delete=models.CASCADE,
        help_text='The plan the customer is subscribed to.'
    )
    description = models.TextField(max_length=1024, blank=True, null=True)
    customer = models.ForeignKey(
        'Customer', related_name='subscriptions', on_delete=models.CASCADE,
        help_text='The customer who is subscribed to the plan.'
    )
    trial_end = models.DateField(
        blank=True, null=True,
        help_text='The date at which the trial ends. '
                  'If set, overrides the computed trial end date from the plan.'
    )
    start_date = models.DateField(
        blank=True, null=True,
        help_text='The starting date for the subscription.'
    )
    cancel_date = models.DateField(
        blank=True, null=True,
        help_text='The date when the subscription was canceled.'
    )
    ended_at = models.DateField(
        blank=True, null=True,
        help_text='The date when the subscription ended.'
    )
    reference = models.CharField(
        max_length=128, blank=True, null=True, validators=[validate_reference],
        help_text="The subscription's reference in an external system."
    )
    state = FSMField(
        choices=STATE_CHOICES, max_length=12, default=STATES.INACTIVE,
        help_text='The state the subscription is in.'
    )
    meta = JSONField(blank=True, null=True, default=dict, encoder=DjangoJSONEncoder)

    def clean(self):
        errors = dict()
        if self.start_date and self.trial_end:
            if self.trial_end < self.start_date:
                errors.update(
                    {'trial_end': "The trial end date cannot be older than "
                                  "the subscription's start date."}
                )
        if self.ended_at:
            if self.state not in [self.STATES.CANCELED, self.STATES.ENDED]:
                errors.update(
                    {'ended_at': 'The ended at date cannot be set if the '
                                 'subscription is not canceled or ended.'}
                )
            elif self.ended_at < self.start_date:
                errors.update(
                    {'ended_at': "The ended at date cannot be older than the"
                                 "subscription's start date."}
                )

        if errors:
            raise ValidationError(errors)

    @property
    def provider(self):
        return self.plan.provider

    def _get_aligned_start_date_after_date(self, reference_date, interval_type,
                                           bymonth=None, byweekday=None, bymonthday=None):
        return list(
            rrule.rrule(interval_type,
                        count=1,  # align the cycle to the given rules as quickly as possible
                        bymonth=bymonth,
                        bymonthday=bymonthday,
                        byweekday=byweekday,
                        dtstart=reference_date)
        )[-1].date()

    def _get_last_start_date_within_range(self, range_start, range_end,
                                          interval_type, interval_count,
                                          bymonth=None, byweekday=None, bymonthday=None):
        # we try to obtain a start date aligned to the given rules
        aligned_start_date = self._get_aligned_start_date_after_date(
            reference_date=range_start,
            interval_type=interval_type,
            bymonth=bymonth,
            bymonthday=bymonthday,
            byweekday=byweekday,
        )

        relative_start_date = range_start if aligned_start_date > range_end else aligned_start_date

        dates = list(
            rrule.rrule(interval_type,
                        dtstart=relative_start_date,
                        interval=interval_count,
                        until=range_end)
        )

        return aligned_start_date if not dates else dates[-1].date()

    def _get_interval_rules(self, granulate, origin_type: OriginType = None):
        if not origin_type:
            origin_type = OriginType.Plan

        interval = self.plan.base_interval if origin_type == OriginType.Plan else self.plan.metered_features_interval
        interval_count = (self.plan.base_interval_count if origin_type == OriginType.Plan
                          else self.plan.metered_features_interval_count)

        rules = {
            'interval_type': self._INTERVALS_CODES[interval],
            'interval_count': 1 if granulate else interval_count,
        }
        if interval == self.plan.INTERVALS.MONTH:
            rules['bymonthday'] = 1  # first day of the month
        elif interval == self.plan.INTERVALS.WEEK:
            rules['byweekday'] = 0  # first day of the week (Monday)
        elif interval == self.plan.INTERVALS.YEAR:
            # first day of the first month (1 Jan)
            rules['bymonth'] = 1
            rules['bymonthday'] = 1

        return rules

    def _cycle_start_date(self, reference_date=None, ignore_trial=None, granulate=None,
                          ignore_start_date=None, origin_type: OriginType = None):
        if not origin_type:
            origin_type = OriginType.Plan

        ignore_trial_default = False
        granulate_default = False
        ignore_start_date_default = False

        ignore_trial = ignore_trial_default or ignore_trial
        granulate = granulate_default or granulate
        ignore_start_date = ignore_start_date_default or ignore_start_date

        if reference_date is None:
            reference_date = timezone.now().date()

        start_date = reference_date

        if not self.start_date or reference_date < self.start_date:
            return None

        rules = self._get_interval_rules(granulate, origin_type)

        start_date_ignoring_trial = self._get_last_start_date_within_range(
            range_start=self.start_date,
            range_end=reference_date,
            **rules
        )

        if ignore_trial or not self.trial_end:
            return start_date_ignoring_trial
        else:  # Trial period is considered
            if self.trial_end < reference_date:  # Trial period ended
                # The day after the trial ended can be a start date (once, right after trial ended)
                date_after_trial_end = self.trial_end + ONE_DAY

                return max(date_after_trial_end, start_date_ignoring_trial)
            else:  # Trial is still ongoing
                if granulate or self.separate_cycles_during_trial:
                    # The trial period is split into cycles according to the rules defined above
                    return start_date_ignoring_trial
                else:
                    # Otherwise, the start date of the trial period is the subscription start date
                    return self.start_date

    def _cycle_end_date(self, reference_date=None, ignore_trial=None, granulate=None, origin_type: OriginType = None):
        if not origin_type:
            origin_type = OriginType.Plan

        ignore_trial_default = False
        granulate_default = False

        ignore_trial = ignore_trial or ignore_trial_default
        granulate = granulate or granulate_default

        if reference_date is None:
            reference_date = timezone.now().date()

        real_cycle_start_date = self._cycle_start_date(reference_date, ignore_trial, granulate, origin_type=origin_type)

        # we need a current start date in order to compute a current end date
        if not real_cycle_start_date:
            return None

        # during trial and trial cycle is not separated into intervals
        if self.on_trial(reference_date) and not (self.separate_cycles_during_trial or granulate):
            return min(self.trial_end, (self.ended_at or datetime.max.date()))

        interval = self.plan.base_interval if origin_type == OriginType.Plan else self.plan.metered_features_interval
        interval_count = (self.plan.base_interval_count if origin_type == OriginType.Plan
                          else self.plan.metered_features_interval_count)

        maximum_cycle_end_date = end_of_interval(
            real_cycle_start_date, interval, interval_count
        )

        # We know that the cycle end_date is the day before the next cycle start_date,
        # therefore we check if the cycle start_date for our maximum cycle end_date is the same
        # as the initial cycle start_date.
        while True:
            reference_cycle_start_date = self._cycle_start_date(maximum_cycle_end_date,
                                                                ignore_trial, granulate, origin_type=origin_type)
            # it means the cycle end_date we got is the right one
            if reference_cycle_start_date == real_cycle_start_date:
                return min(maximum_cycle_end_date, (self.ended_at or datetime.max.date()))
            elif reference_cycle_start_date < real_cycle_start_date:
                # This should never happen in normal conditions, but it may stop infinite looping
                return None

            maximum_cycle_end_date = reference_cycle_start_date - ONE_DAY

    @property
    def prebill_plan(self):
        if self.plan.prebill_plan is not None:
            return self.plan.prebill_plan

        return self.provider.prebill_plan

    @property
    def cycle_billing_duration(self):
        if self.plan.cycle_billing_duration is not None:
            return self.plan.cycle_billing_duration

        return self.provider.cycle_billing_duration

    @property
    def separate_cycles_during_trial(self):
        if self.plan.separate_cycles_during_trial is not None:
            return self.plan.separate_cycles_during_trial

        return self.provider.separate_cycles_during_trial

    @property
    def generate_documents_on_trial_end(self):
        if self.plan.generate_documents_on_trial_end is not None:
            return self.plan.generate_documents_on_trial_end

        return self.provider.generate_documents_on_trial_end

    @property
    def _ignore_trial_end(self):
        return not self.generate_documents_on_trial_end

    def cycle_start_date(self, reference_date=None, origin_type: OriginType = None):
        if not origin_type:
            origin_type = OriginType.Plan

        return self._cycle_start_date(ignore_trial=self._ignore_trial_end,
                                      granulate=False,
                                      reference_date=reference_date,
                                      origin_type=origin_type)

    def cycle_end_date(self, reference_date=None, origin_type: OriginType = None):
        if not origin_type:
            origin_type = OriginType.Plan

        return self._cycle_end_date(ignore_trial=self._ignore_trial_end,
                                    granulate=False,
                                    reference_date=reference_date,
                                    origin_type=origin_type)

    def bucket_start_date(self, reference_date=None, origin_type: OriginType = None):
        if not origin_type:
            origin_type = OriginType.Plan

        granulate = True
        if origin_type == OriginType.Plan:
            granulate = (
                self.plan.separate_plan_entries_per_base_interval != Plan.SEPARATE_ENTRIES_BY_INTERVAL.DISABLED
            )

        return self._cycle_start_date(reference_date=reference_date,
                                      ignore_trial=False, granulate=granulate,
                                      origin_type=origin_type)

    def bucket_end_date(self, reference_date=None, origin_type: OriginType = None):
        if not origin_type:
            origin_type = OriginType.Plan

        granulate = True
        if origin_type == OriginType.Plan:
            granulate = (
                self.plan.separate_plan_entries_per_base_interval != Plan.SEPARATE_ENTRIES_BY_INTERVAL.DISABLED
            )

        return self._cycle_end_date(reference_date=reference_date,
                                    ignore_trial=False, granulate=granulate,
                                    origin_type=origin_type)

    def bucket_start_datetime(self, reference_datetime=None, origin_type: OriginType = None):
        if not origin_type:
            origin_type = OriginType.Plan

        reference_date = reference_datetime.date() if reference_datetime else None

        return datetime.combine(
            self._cycle_start_date(reference_date=reference_date,
                                   ignore_trial=False,
                                   granulate=True,
                                   origin_type=origin_type),
            datetime.min.time(),
            tzinfo=timezone.utc,
        )

    def bucket_end_datetime(self, reference_datetime=None, origin_type: OriginType = None):
        if not origin_type:
            origin_type = OriginType.Plan

        reference_date = reference_datetime.date() if reference_datetime else None

        return datetime.combine(
            self._cycle_end_date(reference_date=reference_date,
                                 ignore_trial=False,
                                 granulate=True,
                                 origin_type=origin_type),
            datetime.max.time(),
            tzinfo=timezone.utc,
        ).replace(microsecond=0)

    def updateable_buckets(self):
        buckets = []

        if self.state in ['ended', 'inactive']:
            return buckets

        start_date = self.bucket_start_date(origin_type=OriginType.MeteredFeature)
        end_date = self.bucket_end_date(origin_type=OriginType.MeteredFeature)

        if start_date is None or end_date is None:
            return buckets

        if self.state == self.STATES.CANCELED:
            if self.cancel_date < start_date:
                return buckets

        buckets.append({'start_date': start_date, 'end_date': end_date})

        generate_after = timedelta(seconds=self.plan.generate_after)
        while (timezone.now() - generate_after <
                datetime.combine(start_date, datetime.min.time()).replace(
                    tzinfo=timezone.get_current_timezone())):
            end_date = start_date - ONE_DAY
            start_date = self.bucket_start_date(end_date, origin_type=OriginType.MeteredFeature)

            if start_date is None:
                return buckets

            buckets.append({'start_date': start_date, 'end_date': end_date})

        return buckets

    @property
    def is_on_trial(self):
        """
        Tells if the subscription is currently on trial.

        :rtype: bool
        """

        if self.state == self.STATES.ACTIVE and self.trial_end:
            return timezone.now().date() <= self.trial_end
        return False

    def on_trial(self, date):
        """
        Tells if the subscription was on trial at the date passed as argument.

        :param date: the date for which the check is made.
        :type date: datetime.date
        :rtype: bool
        """

        if self.trial_end:
            return date <= self.trial_end
        return False

    def _log_should_be_billed_result(self, billing_date, interval_end):
        logger.debug('should_be_billed result: %s', {
            'subscription': self.id,
            'billing_date': billing_date.strftime('%Y-%m-%d'),
            'interval_end': interval_end.strftime('%Y-%m-%d')
        })

    @property
    def billed_up_to_dates(self):
        last_billing_log = self.last_billing_log

        return {
            'metered_features_billed_up_to': last_billing_log.metered_features_billed_up_to,
            'plan_billed_up_to': last_billing_log.plan_billed_up_to
        } if last_billing_log else {
            'metered_features_billed_up_to': self.start_date - ONE_DAY,
            'plan_billed_up_to': self.start_date - ONE_DAY
        }

    def should_be_billed(self, billing_date, generate_documents_datetime=None):
        return (
            self.should_plan_be_billed(billing_date, generate_documents_datetime=generate_documents_datetime) or
            self.should_mfs_be_billed(billing_date, generate_documents_datetime=generate_documents_datetime)
        )

    def should_plan_be_billed(self, billing_date, generate_documents_datetime=None):
        if self.state not in [self.STATES.ACTIVE, self.STATES.CANCELED]:
            return False

        if not generate_documents_datetime:
            generate_documents_datetime = timezone.now()

        if self.cycle_billing_duration:
            if self.start_date > first_day_of_month(billing_date) + self.cycle_billing_duration:
                # There was nothing to bill on the last day of the first cycle billing duration
                return False

            # We need the full cycle here (ignoring trial ends)
            cycle_start_datetime_ignoring_trial = self._cycle_start_date(billing_date,
                                                                         ignore_trial=False)
            latest_possible_billing_datetime = (
                cycle_start_datetime_ignoring_trial + self.cycle_billing_duration
            )

            billing_date = min(billing_date, latest_possible_billing_datetime)

        if billing_date > generate_documents_datetime.date():
            return False

        cycle_start_date = self.cycle_start_date(billing_date)

        if not cycle_start_date:
            return False

        if self.state == self.STATES.CANCELED:
            if billing_date <= self.cancel_date:
                return False

            cycle_start_date = self.cancel_date + ONE_DAY

        cycle_start_datetime = datetime.combine(cycle_start_date,
                                                datetime.min.time()).replace(tzinfo=utc)

        generate_after = timedelta(seconds=self.plan.generate_after)

        if generate_documents_datetime < cycle_start_datetime + generate_after:
            return False

        plan_billed_up_to = self.billed_up_to_dates['plan_billed_up_to']

        # We want to bill the subscription if the plan hasn't been billed for this cycle or
        # if the subscription has been canceled and the plan won't be billed for this cycle.
        if self.prebill_plan or self.state == self.STATES.CANCELED:
            return plan_billed_up_to < cycle_start_date

        # wait until the cycle that is going to be billed ends:
        billed_cycle_end_date = self.cycle_end_date(plan_billed_up_to + ONE_DAY)
        return billed_cycle_end_date < cycle_start_date

    def should_mfs_be_billed(self, billing_date, generate_documents_datetime=None, billed_up_to=None):
        if self.state not in [self.STATES.ACTIVE, self.STATES.CANCELED]:
            return False

        if not generate_documents_datetime:
            generate_documents_datetime = timezone.now()

        if (
            self.plan.only_bill_metered_features_with_base_amount and
            not self.should_plan_be_billed(billing_date, generate_documents_datetime)
        ):
            return False

        if self.cycle_billing_duration:
            if self.start_date > first_day_of_month(billing_date) + self.cycle_billing_duration:
                # There was nothing to bill on the last day of the first cycle billing duration
                return False

            # We need the full cycle here (ignoring trial ends)
            cycle_start_datetime_ignoring_trial = self._cycle_start_date(billing_date,
                                                                         ignore_trial=False,
                                                                         origin_type=OriginType.MeteredFeature)
            latest_possible_billing_datetime = (
                cycle_start_datetime_ignoring_trial + self.cycle_billing_duration
            )

            billing_date = min(billing_date, latest_possible_billing_datetime)

        if billing_date > generate_documents_datetime.date():
            return False

        cycle_start_date = self.cycle_start_date(billing_date, origin_type=OriginType.MeteredFeature)

        if not cycle_start_date:
            return False

        if self.state == self.STATES.CANCELED:
            if billing_date <= self.cancel_date:
                return False

            cycle_start_date = self.cancel_date + ONE_DAY

        cycle_start_datetime = datetime.combine(cycle_start_date,
                                                datetime.min.time()).replace(tzinfo=utc)

        generate_after = timedelta(seconds=self.plan.generate_after)

        if generate_documents_datetime < cycle_start_datetime + generate_after:
            return False

        metered_features_billed_up_to = billed_up_to or self.billed_up_to_dates['metered_features_billed_up_to']

        # We want to bill the subscription if the subscription has been canceled.
        if self.state == self.STATES.CANCELED:
            return metered_features_billed_up_to < cycle_start_date

        # wait until the cycle that is going to be billed ends:
        billed_cycle_end_date = self.cycle_end_date(metered_features_billed_up_to + ONE_DAY,
                                                    origin_type=OriginType.MeteredFeature)

        return billed_cycle_end_date < cycle_start_date and billed_cycle_end_date < billing_date

    @property
    def _has_existing_customer_with_consolidated_billing(self):
        # TODO: move to Customer
        return (
            self.customer.consolidated_billing and
            self.customer.subscriptions.filter(state=self.STATES.ACTIVE).count() > 1
        )

    @property
    def is_billed_first_time(self):
        return self.billing_logs.all().count() == 0

    @property
    def last_billing_log(self):
        return self.billing_logs.order_by('billing_date').last()

    @property
    def last_billing_date(self):
        # ToDo: Improve this when dropping Django 1.8 support
        try:
            return self.billing_logs.all()[0].billing_date
        except (BillingLog.DoesNotExist, IndexError):
            # It should never get here.
            return None

    def _should_activate_with_free_trial(self):
        return Subscription.objects.filter(
            plan__provider=self.plan.provider,
            customer=self.customer,
            state__in=[Subscription.STATES.ACTIVE, Subscription.STATES.CANCELED,
                       Subscription.STATES.ENDED]
        ).count() == 0

    @property
    def applied_discounts(self):
        Discount = apps.get_model('silver.Discount')

        return Discount.for_subscription(self)

    @property
    def applied_bonuses(self):
        Bonus = apps.get_model('silver.Bonus')

        return Bonus.for_subscription(self)

    ##########################################################################
    # STATE MACHINE TRANSITIONS
    ##########################################################################
    @transition(field=state, source=[STATES.INACTIVE, STATES.CANCELED],
                target=STATES.ACTIVE)
    def activate(self, start_date=None, trial_end_date=None):
        if start_date:
            self.start_date = min(timezone.now().date(), start_date)
        else:
            if self.start_date:
                self.start_date = min(timezone.now().date(), self.start_date)
            else:
                self.start_date = timezone.now().date()

        if self._should_activate_with_free_trial():
            if trial_end_date:
                self.trial_end = max(self.start_date, trial_end_date)
            else:
                if self.trial_end:
                    if self.trial_end < self.start_date:
                        self.trial_end = None
                elif self.plan.trial_period_days:
                    self.trial_end = self.start_date + timedelta(
                        days=self.plan.trial_period_days - 1)

    @transition(field=state, source=STATES.ACTIVE, target=STATES.CANCELED)
    def cancel(self, when):
        now = timezone.now()

        if isinstance(when, date):
            self.cancel_date = when

        elif when == self.CANCEL_OPTIONS.END_OF_BILLING_CYCLE:
            if self.is_on_trial:
                self.cancel_date = self.bucket_end_date(reference_date=self.trial_end)
            else:
                self.cancel_date = self.cycle_end_date()

        elif when == self.CANCEL_OPTIONS.NOW:
            bsdt = self.bucket_start_datetime()
            bedt = self.bucket_end_datetime()

            for metered_feature in self.plan.metered_features.all():
                MeteredFeatureUnitsLog.objects.filter(
                    start_datetime__gte=bsdt, end_datetime=bedt,
                    metered_feature=metered_feature.pk,
                    subscription=self.pk
                ).update(end_datetime=now)

            self.cancel_date = now.date()

        if self.on_trial(now.date()):
            self.trial_end = min(self.trial_end, self.cancel_date)

        self.save()

    @transition(field=state, source=STATES.CANCELED, target=STATES.ENDED)
    def end(self):
        self.ended_at = timezone.now().date()
    ##########################################################################

    def _cancel_now(self):
        self.cancel(when=self.CANCEL_OPTIONS.NOW)

    def _cancel_at_end_of_billing_cycle(self):
        self.cancel(when=self.CANCEL_OPTIONS.END_OF_BILLING_CYCLE)

    def _get_interval_end_date(self, date=None):
        """
        :returns: the end date of the interval that should be billed. The
            returned value is a function f(subscription_state, date)
        :rtype: datetime.date
        """

        if self.state == self.STATES.ACTIVE:
            end_date = self.bucket_end_date(reference_date=date)
        elif self.state == self.STATES.CANCELED:
            if self.trial_end and date <= self.trial_end:
                if self.trial_end <= self.cancel_date:
                    end_date = self.trial_end
                else:
                    end_date = self.cancel_date
            else:
                end_date = self.cancel_date
        return end_date

    def _log_value_state(self, value_state):
        logger.debug('Adding value: %s', {
            'subscription': self.id,
            'value_state': value_state
        })

    def _add_plan_trial(self, start_date, end_date, invoice=None,
                        proforma=None):
        """
        Adds the plan trial to the document, by adding an entry with positive
        prorated value and one with prorated, negative value which represents
        the discount for the trial period.
        """

        prorated, fraction = self._get_proration_status_and_fraction(start_date,
                                                                     end_date,
                                                                     OriginType.Plan)
        plan_price = quantize_fraction(Fraction(str(self.plan.amount)) * fraction)

        context = self._build_entry_context({
            'name': self.plan.name,
            'unit': self.plan.base_interval,
            'product_code': self.plan.product_code,
            'start_date': start_date,
            'end_date': end_date,
            'prorated': prorated,
            'proration_percentage': plan_price,
            'context': 'plan-trial'
        })

        unit = self._entry_unit(context)

        description = self._entry_description(context)

        # Add plan with positive value
        DocumentEntry.objects.create(
            invoice=invoice, proforma=proforma, description=description,
            unit=unit, unit_price=plan_price, quantity=Decimal('1.00'),
            product_code=self.plan.product_code, prorated=prorated,
            start_date=start_date, end_date=end_date
        )

        context.update({
            'context': 'plan-trial-discount'
        })

        description = self._entry_description(context)

        # Add plan with negative value
        DocumentEntry.objects.create(
            invoice=invoice, proforma=proforma, description=description,
            unit=unit, unit_price=-plan_price, quantity=Decimal('1.00'),
            product_code=self.plan.product_code, prorated=prorated,
            start_date=start_date, end_date=end_date
        )

        return Decimal("0.00")

    # def _get_proration_status_and_fraction_during_trial(self, start_date, end_date) -> Tuple[bool, Fraction]:
    #     """
    #     Returns the proration percent (how much of the interval will be billed)
    #     and the status (if the subscription is prorated or not) during the trial period.
    #     If start_date and end_date are not from the trial period, you are entering
    #     undefined behaviour territory.
    #
    #     :returns: a tuple containing (status, Decimal(percent)) where status
    #         can be one of [True, False]. The Decimal will have values in the
    #         [0.00, 1.00] range.
    #     :rtype: tuple
    #     """
    #
    #     if self.on_trial(end_date):
    #         fraction = Fraction((end_date - start_date).days + 1, (self.start_date - self.trial_end).days + 1)
    #
    #         return fraction != Fraction(1), fraction
    #
    #     return False, Fraction(1)

    def _get_consumed_units_from_total_included_in_trial(self, metered_feature, start_date, end_date,
                                                         consumed_units, bonuses=None):
        """
        :returns: (consumed_units, free_units)
        """

        # _, extra_proration_fraction = self._get_proration_status_and_fraction_during_trial(start_date, end_date)
        #
        # included_units_during_trial = quantize_fraction(
        #     Fraction(str(metered_feature.included_units_during_trial)) * extra_proration_fraction
        # )

        included_units_during_trial = metered_feature.included_units_during_trial

        if included_units_during_trial is None:
            return 0, consumed_units

        if consumed_units <= included_units_during_trial:
            return 0, consumed_units

        return consumed_units - included_units_during_trial, included_units_during_trial

    def _get_extra_consumed_units_during_trial(self, metered_feature, start_date, end_date,
                                               consumed_units, bonuses=None):
        """
        :returns: (extra_consumed, free_units)
            extra_consumed - units consumed extra during trial that will be
                billed
            free_units - the units included in trial
        """

        if self.is_billed_first_time:
            # It's on trial and is billed first time
            return self._get_consumed_units_from_total_included_in_trial(
                metered_feature, start_date, end_date, consumed_units, bonuses=bonuses
            )
        else:
            # It's still on trial but has been billed before
            # The following part tries to handle the case when the trial
            # spans over 2 months and the subscription has been already billed
            # once => this month it is still on trial but it only
            # has remaining = consumed_last_cycle - included_during_trial
            last_log_entry = self.billing_logs.all()[0]
            if last_log_entry.invoice:
                qs = last_log_entry.invoice.invoice_entries.filter(
                    product_code=metered_feature.product_code)
            elif last_log_entry.proforma:
                qs = last_log_entry.proforma.proforma_entries.filter(
                    product_code=metered_feature.product_code)
            else:
                qs = DocumentEntry.objects.none()

            if not qs.exists():
                return self._get_consumed_units_from_total_included_in_trial(
                    metered_feature, start_date, end_date, consumed_units, bonuses=bonuses
                )

            consumed = [qs_item.quantity
                        for qs_item in qs if qs_item.unit_price >= 0]
            consumed_in_last_billing_cycle = sum(consumed)

            included_during_trial = metered_feature.included_units_during_trial or Decimal(0)

            if consumed_in_last_billing_cycle > included_during_trial:
                return consumed_units, 0

            remaining = included_during_trial - consumed_in_last_billing_cycle
            if consumed_units > remaining:
                return consumed_units - remaining, remaining

            return 0, consumed_units

    def _add_mfs_for_trial(self, start_date, end_date, invoice=None, proforma=None, bonuses=None):
        start_datetime = datetime.combine(
            start_date,
            datetime.min.time(),
            tzinfo=timezone.utc,
        ).replace(microsecond=0)

        end_datetime = datetime.combine(
            end_date,
            datetime.max.time(),
            tzinfo=timezone.utc,
        ).replace(microsecond=0)

        prorated, fraction = self._get_proration_status_and_fraction(start_date,
                                                                     end_date,
                                                                     OriginType.MeteredFeature)
        context = self._build_entry_context({
            'product_code': self.plan.product_code,
            'start_date': start_date,
            'end_date': end_date,
            'prorated': prorated,
            'proration_percentage': quantize_fraction(fraction),
            'bonuses': bonuses,
            'context': 'metered-feature-trial'
        })

        total = Decimal("0.00")

        # Add all the metered features consumed during the trial period
        for metered_feature in self.plan.metered_features.all():
            context.update({'metered_feature': metered_feature,
                            'unit': metered_feature.unit,
                            'name': metered_feature.name,
                            'product_code': metered_feature.product_code})

            unit = self._entry_unit(context)

            qs = self.mf_log_entries.filter(metered_feature=metered_feature,
                                            start_datetime__gte=start_datetime,
                                            end_datetime__lte=end_datetime)
            log = [qs_item.consumed_units for qs_item in qs]
            total_consumed_units = sum(log)

            mf_bonuses = [bonus for bonus in bonuses if bonus.applies_to_metered_feature(metered_feature)]

            extra_consumed, free = self._get_extra_consumed_units_during_trial(
                metered_feature, start_date, end_date, total_consumed_units, bonuses=mf_bonuses
            )

            if extra_consumed > 0:
                charged_units = extra_consumed
                free_units = free
            else:
                free_units = total_consumed_units
                charged_units = 0

            if free_units > 0:
                description = self._entry_description(context)

                # Positive value for the consumed items.
                DocumentEntry.objects.create(
                    invoice=invoice, proforma=proforma, description=description,
                    unit=unit, quantity=free_units,
                    unit_price=metered_feature.price_per_unit,
                    product_code=metered_feature.product_code,
                    start_date=start_date, end_date=end_date,
                    prorated=prorated
                )

                context.update({
                    'context': 'metered-feature-trial-discount'
                })

                description = self._entry_description(context)

                # Negative value for the consumed items.
                DocumentEntry.objects.create(
                    invoice=invoice, proforma=proforma, description=description,
                    unit=unit, quantity=free_units,
                    unit_price=-metered_feature.price_per_unit,
                    product_code=metered_feature.product_code,
                    start_date=start_date, end_date=end_date,
                    prorated=prorated
                )

            # Extra items consumed items that are not included
            if charged_units > 0:
                context.update({
                    'context': 'metered-feature-trial-not-discounted'
                })

                description_template_path = field_template_path(
                    field='entry_description',
                    provider=self.plan.provider.slug)
                description = render_to_string(
                    description_template_path, context
                )

                total += DocumentEntry.objects.create(
                    invoice=invoice, proforma=proforma,
                    description=description, unit=unit,
                    quantity=charged_units, prorated=prorated,
                    unit_price=metered_feature.price_per_unit,
                    product_code=metered_feature.product_code,
                    start_date=start_date, end_date=end_date
                ).total

        return total

    def _add_plan_entries(self, start_date, end_date, invoice=None, proforma=None) \
            -> Tuple[Decimal, List['silver.models.DocumentEntry']]:
        """
        Adds to the document the cost of the plan.
        :returns: A tuple consisting of:
            - The plan cost after proration and PER ENTRY discounts have been applied.
            - A list of entries that have been added to the documents. The first one is the (prorated)
              cost of the plan, followed by PER ENTRY discount entries if applicable. It is possible
              that PER DOCUMENT or PER ENTRY TYPE discount entries to be created later down the
              document generation process.
        """

        prorated, fraction = self._get_proration_status_and_fraction(start_date,
                                                                     end_date,
                                                                     OriginType.Plan)

        plan_price = quantize_fraction(Fraction(str(self.plan.amount)) * fraction)

        base_context = {
            'name': self.plan.name,
            'unit': self.plan.base_interval,
            'product_code': self.plan.product_code,
            'start_date': start_date,
            'end_date': end_date,
            'prorated': prorated,
            'proration_percentage': quantize_fraction(fraction),
        }

        plan_context = base_context.copy()
        plan_context.update({
            'context': 'plan'
        })

        context = self._build_entry_context(plan_context)
        description = self._entry_description(context)
        unit = self._entry_unit(context)

        entries = [
            DocumentEntry.objects.create(
                invoice=invoice, proforma=proforma, description=description,
                unit=unit, unit_price=plan_price, quantity=Decimal('1.00'),
                product_code=self.plan.product_code, prorated=prorated,
                start_date=start_date, end_date=end_date
            )
        ]

        return entries[0].total_before_tax, entries

    def _included_units_from_bonuses(
        self, metered_feature, start_date, end_date, extra_proration_fraction: Fraction, bonuses: List
    ):
        included_units = extra_proration_fraction * Fraction(metered_feature.included_units or Decimal(0))

        return sum(
            [
                (
                    Fraction(str(bonus.amount)) if bonus.amount else
                    Fraction(str(bonus.amount_percentage)) / 100 * included_units
                ) * bonus.extra_proration_fraction(self, start_date, end_date, OriginType.MeteredFeature)[0]
                for bonus in bonuses
            ]
        )

    def _get_extra_consumed_units(self, metered_feature, extra_proration_fraction: Fraction,
                                  start_datetime, end_datetime, bonuses=None) -> OverageInfo:
        included_units = extra_proration_fraction * Fraction(metered_feature.included_units or Decimal(0))

        log_entries = self.mf_log_entries.filter(
            metered_feature=metered_feature,
            start_datetime__gte=start_datetime,
            end_datetime__lte=end_datetime
        )

        consumed_units = [entry.consumed_units for entry in log_entries]
        total_consumed_units = reduce(lambda x, y: x + y, consumed_units, 0)

        annotations = list({log_entry.annotation for log_entry in log_entries})

        start_date = start_datetime.date()
        end_date = end_datetime.date()

        if bonuses:
            bonuses = [bonus for bonus in bonuses if bonus.matches_metered_feature_units(metered_feature, annotations)]

        applied_directly_bonuses = [
            bonus for bonus in bonuses
            if bonus.document_entry_behavior == bonus.ENTRY_BEHAVIOR.APPLY_DIRECTLY_TO_TARGET_ENTRIES
        ]

        applied_separately_bonuses = [
            bonus for bonus in bonuses
            if bonus.document_entry_behavior == bonus.ENTRY_BEHAVIOR.APPLY_AS_SEPARATE_ENTRY_PER_ENTRY
        ]

        included_units += self._included_units_from_bonuses(
            metered_feature, start_date, end_date, extra_proration_fraction, applied_directly_bonuses
        )

        included_units = quantize_fraction(included_units)

        extra_consumed_units = max(total_consumed_units - included_units, Decimal(0))

        return OverageInfo(
            extra_consumed_units, annotations, applied_directly_bonuses, applied_separately_bonuses
        )

    def _add_mfs_entries(self, start_date, end_date, invoice=None, proforma=None, bonuses=None) \
            -> Tuple[Decimal, List['silver.models.DocumentEntry']]:
        start_datetime = datetime.combine(
            start_date,
            datetime.min.time(),
            tzinfo=timezone.utc,
        ).replace(microsecond=0)

        end_datetime = datetime.combine(
            end_date,
            datetime.max.time(),
            tzinfo=timezone.utc,
        ).replace(microsecond=0)

        prorated, fraction = self._get_proration_status_and_fraction(start_date, end_date, OriginType.MeteredFeature)

        base_context = self._build_entry_context({
            'start_date': start_date,
            'end_date': end_date,
            'prorated': prorated,
            'proration_percentage': quantize_fraction(fraction),
            'context': 'metered-feature'
        })

        mfs_total = Decimal('0.00')
        entries = []
        for metered_feature in self.plan.metered_features.all():
            overage_info = self._get_extra_consumed_units(
                metered_feature, fraction, start_datetime, end_datetime, bonuses=bonuses
            )
            extra_consumed_units = overage_info.extra_consumed_units

            entry_context = base_context.copy()
            entry_context.update({
                'metered_feature': metered_feature,
                'unit': metered_feature.unit,
                'name': metered_feature.name,
                'product_code': metered_feature.product_code,
                'annotations': overage_info.annotations,
                'directly_applied_bonuses': overage_info.directly_applied_bonuses,
            })

            description = self._entry_description(entry_context)
            unit = self._entry_unit(entry_context)

            entry = DocumentEntry.objects.create(
                invoice=invoice, proforma=proforma,
                description=description, unit=unit,
                quantity=overage_info.extra_consumed_units, prorated=prorated,
                unit_price=metered_feature.price_per_unit,
                product_code=metered_feature.product_code,
                start_date=start_date, end_date=end_date
            )
            entries.append(entry)

            for separate_bonus in overage_info.separately_applied_bonuses:
                if extra_consumed_units <= 0:
                    break

                bonus_included_units = quantize_fraction(
                    self._included_units_from_bonuses(
                        metered_feature, start_date, end_date,
                        extra_proration_fraction=fraction, bonuses=[separate_bonus]
                    )
                )
                if not bonus_included_units:
                    continue

                bonus_consumed_units = min(bonus_included_units, extra_consumed_units)
                extra_consumed_units -= bonus_consumed_units

                bonus_entry_context = base_context.copy()
                bonus_entry_context.update({
                    'metered_feature': metered_feature,
                    'unit': metered_feature.unit,
                    'name': metered_feature.name,
                    'product_code': metered_feature.product_code,
                    'annotations': overage_info.annotations,
                    'directly_applied_bonuses': overage_info.directly_applied_bonuses,
                    'context': 'metered-feature-bonus'
                })

                description = self._entry_description(bonus_entry_context)

                bonus_entry = DocumentEntry.objects.create(
                    invoice=invoice, proforma=proforma,
                    description=description, unit=unit,
                    quantity=bonus_consumed_units, prorated=prorated,
                    unit_price=-metered_feature.price_per_unit,
                    product_code=separate_bonus.product_code,
                    start_date=start_date, end_date=end_date
                )
                entries.append(bonus_entry)
                mfs_total += bonus_entry.total_before_tax

            mfs_total += entry.total_before_tax

        return mfs_total, entries

    def _get_proration_status_and_fraction(self, start_date, end_date, entry_type: OriginType) -> Tuple[bool, Fraction]:
        """
        Returns the proration percent (how much of the interval will be billed)
        and the status (if the subscription is prorated or not).
        If start_date and end_date are not from the same billing cycle, you are entering
        undefined behaviour territory.

        :returns: a tuple containing (status, Decimal(percent)) where status
            can be one of [True, False]. The Decimal will have values in the
            [0.00, 1.00] range.
        :rtype: tuple
        """

        interval = self.plan.base_interval if entry_type == OriginType.Plan else self.plan.metered_features_interval
        interval_count = (self.plan.base_interval_count if entry_type == OriginType.Plan else
                          self.plan.metered_features_interval_count)

        cycle_start_date = self._cycle_start_date(
            ignore_trial=True,
            reference_date=start_date,
            origin_type=entry_type
        )

        first_day_of_full_interval = first_day_of_interval(cycle_start_date, interval)
        last_day_of_full_interval = end_of_interval(
            first_day_of_full_interval, interval, interval_count
        )

        if start_date == first_day_of_full_interval and end_date == last_day_of_full_interval:
            return False, Fraction(1, 1)

        if interval in (Plan.INTERVALS.DAY, Plan.INTERVALS.WEEK, Plan.INTERVALS.YEAR):
            full_interval_days = (last_day_of_full_interval - first_day_of_full_interval).days + 1
            billing_cycle_days = (end_date - start_date).days + 1
            return (
                True,
                Fraction(billing_cycle_days, full_interval_days)
            )
        elif interval == Plan.INTERVALS.MONTH:
            billing_cycle_months = monthdiff_as_fraction(end_date + ONE_DAY, start_date)
            full_interval_months = monthdiff_as_fraction(last_day_of_full_interval + ONE_DAY,
                                                         first_day_of_full_interval)

            return True, Fraction(billing_cycle_months, full_interval_months)

    def _entry_unit(self, context):
        unit_template_path = field_template_path(
            field='entry_unit', provider=self.plan.provider.slug)
        return render_to_string(unit_template_path, context)

    def _entry_description(self, context):
        description_template_path = field_template_path(
            field='entry_description', provider=self.plan.provider.slug
        )
        return render_to_string(description_template_path, context)

    @property
    def _base_entry_context(self):
        return {
            'name': None,
            'unit': 1,
            'subscription': self,
            'plan': self.plan,
            'provider': self.plan.provider,
            'customer': self.customer,
            'product_code': None,
            'start_date': None,
            'end_date': None,
            'prorated': None,
            'proration_percentage': None,
            'metered_feature': None,
            'context': None
        }

    def _build_entry_context(self, context):
        base_context = self._base_entry_context
        base_context.update(context)
        return base_context

    def __str__(self):
        return u'%s (%s)' % (self.customer, self.plan.name)


class BillingLog(models.Model):
    subscription = models.ForeignKey('Subscription', on_delete=models.CASCADE,
                                     related_name='billing_logs')
    invoice = models.ForeignKey('BillingDocumentBase', null=True, blank=True,
                                on_delete=models.SET_NULL, related_name='invoice_billing_logs')
    proforma = models.ForeignKey('BillingDocumentBase', null=True, blank=True,
                                 on_delete=models.SET_NULL, related_name='proforma_billing_logs')
    billing_date = models.DateField(
        help_text="The date when the invoice/proforma was generated."
    )
    plan_billed_up_to = models.DateField(
        help_text="The date up to which the plan base amount has been billed."
    )
    metered_features_billed_up_to = models.DateField(
        help_text="The date up to which the metered features have been billed."
    )
    total = models.DecimalField(
        decimal_places=2, max_digits=12,
        null=True, blank=True
    )
    plan_amount = models.DecimalField(
        decimal_places=2, max_digits=12,
        null=True, blank=True
    )
    metered_features_amount = models.DecimalField(
        decimal_places=2, max_digits=12,
        null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=timezone.now)

    class Meta:
        ordering = ['-billing_date']

    def __str__(self):
        return u'{sub} - {pro} - {inv} - {date}'.format(
            sub=self.subscription, pro=self.proforma,
            inv=self.invoice, date=self.billing_date)


@receiver(pre_delete, sender=Customer)
def cancel_billing_documents(sender, instance, **kwargs):
    if instance.pk and not kwargs.get('raw', False):
        subscriptions = Subscription.objects.filter(
            customer=instance, state=Subscription.STATES.ACTIVE
        )
        for subscription in subscriptions:
            try:
                subscription.cancel()
                subscription.end()
                subscription.save()
            except TransitionNotAllowed:
                logger.error(
                    'Couldn\'t end subscription on customer delete: %s', {
                        'subscription': subscription.id,
                    }
                )
                pass
