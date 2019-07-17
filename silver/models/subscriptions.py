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

import calendar
import logging

from datetime import date, datetime, timedelta
from decimal import Decimal
from functools import reduce

from annoying.fields import JSONField
from annoying.functions import get_object_or_None
from dateutil import rrule
from django_fsm import FSMField, transition, TransitionNotAllowed
from model_utils import Choices

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.template import TemplateDoesNotExist
from django.template.loader import get_template, render_to_string
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible
from django.utils.timezone import utc
from django.utils.translation import ugettext_lazy as _

from silver.models.billing_entities import Customer
from silver.models.documents import DocumentEntry
from silver.utils.dates import ONE_DAY, relativedelta, first_day_of_month
from silver.validators import validate_reference


logger = logging.getLogger(__name__)


def field_template_path(field, provider=None):
    if provider:
        provider_template_path = 'billing_documents/{provider}/{field}.html'.\
            format(provider=provider, field=field)
        try:
            get_template(provider_template_path)
            return provider_template_path
        except TemplateDoesNotExist:
            pass
    return 'billing_documents/{field}.html'.format(field=field)


@python_2_unicode_compatible
class MeteredFeatureUnitsLog(models.Model):
    metered_feature = models.ForeignKey('MeteredFeature', related_name='consumed',
                                        on_delete=models.CASCADE)
    subscription = models.ForeignKey('Subscription', related_name='mf_log_entries',
                                     on_delete=models.CASCADE)
    consumed_units = models.DecimalField(max_digits=19, decimal_places=4,
                                         validators=[MinValueValidator(0.0)])
    start_date = models.DateField(editable=False)
    end_date = models.DateField(editable=False)

    class Meta:
        unique_together = ('metered_feature', 'subscription', 'start_date',
                           'end_date')

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
            start_date = self.subscription.bucket_start_date()
            end_date = self.subscription.bucket_end_date()
            if get_object_or_None(MeteredFeatureUnitsLog, start_date=start_date,
                                  end_date=end_date,
                                  metered_feature=self.metered_feature,
                                  subscription=self.subscription):
                err_msg = 'A %s units log for the current date already exists.'\
                          ' You can edit that one.' % self.metered_feature
                raise ValidationError(err_msg)

    def save(self, *args, **kwargs):
        if not self.id:
            if not self.start_date:
                self.start_date = self.subscription.bucket_start_date()
            if not self.end_date:
                self.end_date = self.subscription.bucket_end_date()
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


@python_2_unicode_compatible
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
    description = models.CharField(max_length=1024, blank=True, null=True)
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
        protected=True, help_text='The state the subscription is in.'
    )
    meta = JSONField(blank=True, null=True, default={})

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

    def _cycle_start_date(self, reference_date=None, ignore_trial=None, granulate=None):
        ignore_trial_default = False
        granulate_default = False

        ignore_trial = ignore_trial_default or ignore_trial
        granulate = granulate_default or granulate

        if reference_date is None:
            reference_date = timezone.now().date()

        if not self.start_date or reference_date < self.start_date:
            return None

        rules = {
            'interval_type': self._INTERVALS_CODES[self.plan.interval],
            'interval_count': 1 if granulate else self.plan.interval_count,
        }
        if self.plan.interval == self.plan.INTERVALS.MONTH:
            rules['bymonthday'] = 1  # first day of the month
        elif self.plan.interval == self.plan.INTERVALS.WEEK:
            rules['byweekday'] = 0  # first day of the week (Monday)
        elif self.plan.interval == self.plan.INTERVALS.YEAR:
            # first day of the first month (1 Jan)
            rules['bymonth'] = 1
            rules['bymonthday'] = 1

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

    def _cycle_end_date(self, reference_date=None, ignore_trial=None, granulate=None):
        ignore_trial_default = False
        granulate_default = False

        ignore_trial = ignore_trial or ignore_trial_default
        granulate = granulate or granulate_default

        if reference_date is None:
            reference_date = timezone.now().date()

        real_cycle_start_date = self._cycle_start_date(reference_date, ignore_trial, granulate)

        # we need a current start date in order to compute a current end date
        if not real_cycle_start_date:
            return None

        # during trial and trial cycle is not separated into intervals
        if self.on_trial(reference_date) and not (self.separate_cycles_during_trial or
                                                  granulate):
            return min(self.trial_end, (self.ended_at or datetime.max.date()))

        if self.plan.interval == self.plan.INTERVALS.YEAR:
            relative_delta = {'years': self.plan.interval_count}
        elif self.plan.interval == self.plan.INTERVALS.MONTH:
            relative_delta = {'months': self.plan.interval_count}
        elif self.plan.interval == self.plan.INTERVALS.WEEK:
            relative_delta = {'weeks': self.plan.interval_count}
        else:  # plan.INTERVALS.DAY
            relative_delta = {'days': self.plan.interval_count}

        maximum_cycle_end_date = real_cycle_start_date + relativedelta(**relative_delta) - ONE_DAY

        # We know that the cycle end_date is the day before the next cycle start_date,
        # therefore we check if the cycle start_date for our maximum cycle end_date is the same
        # as the initial cycle start_date.
        while True:
            reference_cycle_start_date = self._cycle_start_date(maximum_cycle_end_date,
                                                                ignore_trial, granulate)
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

    def cycle_start_date(self, reference_date=None):
        return self._cycle_start_date(ignore_trial=self._ignore_trial_end,
                                      granulate=False,
                                      reference_date=reference_date)

    def cycle_end_date(self, reference_date=None):
        return self._cycle_end_date(ignore_trial=self._ignore_trial_end,
                                    granulate=False,
                                    reference_date=reference_date)

    def bucket_start_date(self, reference_date=None):
        return self._cycle_start_date(reference_date=reference_date,
                                      ignore_trial=False, granulate=True)

    def bucket_end_date(self, reference_date=None):
        return self._cycle_end_date(reference_date=reference_date,
                                    ignore_trial=False, granulate=True)

    def updateable_buckets(self):
        buckets = []

        if self.state in ['ended', 'inactive']:
            return buckets

        start_date = self.bucket_start_date()
        end_date = self.bucket_end_date()

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
            start_date = self.bucket_start_date(end_date)
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

        billed_up_to_dates = self.billed_up_to_dates
        plan_billed_up_to = billed_up_to_dates['plan_billed_up_to']
        metered_features_billed_up_to = billed_up_to_dates['metered_features_billed_up_to']

        # We want to bill the subscription if the plan hasn't been billed for this cycle or
        # if the subscription has been canceled and the plan won't be billed for this cycle.
        if self.prebill_plan or self.state == self.STATES.CANCELED:
            plan_should_be_billed = plan_billed_up_to < cycle_start_date

            if self.state == self.STATES.CANCELED:
                return metered_features_billed_up_to < cycle_start_date or plan_should_be_billed

            return plan_should_be_billed

        # wait until the cycle that is going to be billed ends:
        billed_cycle_end_date = self.cycle_end_date(plan_billed_up_to + ONE_DAY)
        return billed_cycle_end_date < cycle_start_date

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
        now = timezone.now().date()
        bsd = self.bucket_start_date()
        bed = self.bucket_end_date()

        if when == self.CANCEL_OPTIONS.END_OF_BILLING_CYCLE:
            if self.is_on_trial:
                self.cancel_date = self.bucket_end_date(reference_date=self.trial_end)
            else:
                self.cancel_date = self.cycle_end_date()
        elif when == self.CANCEL_OPTIONS.NOW:
            for metered_feature in self.plan.metered_features.all():
                log = MeteredFeatureUnitsLog.objects.filter(
                    start_date=bsd, end_date=bed,
                    metered_feature=metered_feature.pk,
                    subscription=self.pk).first()
                if log:
                    log.end_date = now
                    log.save()
            if self.on_trial(now):
                self.trial_end = now
            self.cancel_date = now

        self.save()

    @transition(field=state, source=STATES.CANCELED, target=STATES.ENDED)
    def end(self):
        self.ended_at = timezone.now().date()
    ##########################################################################

    def _cancel_now(self):
        self.cancel(when=self.CANCEL_OPTIONS.NOW)

    def _cancel_at_end_of_billing_cycle(self):
        self.cancel(when=self.CANCEL_OPTIONS.END_OF_BILLING_CYCLE)

    def _add_trial_value(self, start_date, end_date, invoice=None,
                         proforma=None):
        self._add_plan_trial(start_date=start_date, end_date=end_date,
                             invoice=invoice, proforma=proforma)
        self._add_mfs_for_trial(start_date=start_date, end_date=end_date,
                                invoice=invoice, proforma=proforma)

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

        prorated, percent = self._get_proration_status_and_percent(start_date,
                                                                   end_date)
        plan_price = self.plan.amount * percent

        context = self._build_entry_context({
            'name': self.plan.name,
            'unit': self.plan.interval,
            'product_code': self.plan.product_code,
            'start_date': start_date,
            'end_date': end_date,
            'prorated': prorated,
            'proration_percentage': percent,
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

    def _get_consumed_units_from_total_included_in_trial(self, metered_feature,
                                                         consumed_units):
        """
        :returns: (consumed_units, free_units)
        """

        if metered_feature.included_units_during_trial:
            included_units_during_trial = metered_feature.included_units_during_trial
            if consumed_units > included_units_during_trial:
                extra_consumed = consumed_units - included_units_during_trial
                return extra_consumed, included_units_during_trial
            else:
                return 0, consumed_units
        elif metered_feature.included_units_during_trial == Decimal('0.0000'):
            return consumed_units, 0
        elif metered_feature.included_units_during_trial is None:
            return 0, consumed_units

    def _get_extra_consumed_units_during_trial(self, metered_feature,
                                               consumed_units):
        """
        :returns: (extra_consumed, free_units)
            extra_consumed - units consumed extra during trial that will be
                billed
            free_units - the units included in trial
        """

        if self.is_billed_first_time:
            # It's on trial and is billed first time
            return self._get_consumed_units_from_total_included_in_trial(
                metered_feature, consumed_units)
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
                    metered_feature, consumed_units)

            consumed = [qs_item.quantity
                        for qs_item in qs if qs_item.unit_price >= 0]
            consumed_in_last_billing_cycle = sum(consumed)

            if metered_feature.included_units_during_trial:
                included_during_trial = metered_feature.included_units_during_trial
                if consumed_in_last_billing_cycle > included_during_trial:
                    return consumed_units, 0
                else:
                    remaining = included_during_trial - consumed_in_last_billing_cycle
                    if consumed_units > remaining:
                        return consumed_units - remaining, remaining
                    elif consumed_units <= remaining:
                        return 0, consumed_units
            return 0, consumed_units

    def _add_mfs_for_trial(self, start_date, end_date, invoice=None,
                           proforma=None):
        prorated, percent = self._get_proration_status_and_percent(start_date,
                                                                   end_date)
        context = self._build_entry_context({
            'product_code': self.plan.product_code,
            'start_date': start_date,
            'end_date': end_date,
            'prorated': prorated,
            'proration_percentage': percent,
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
                                            start_date__gte=start_date,
                                            end_date__lte=end_date)
            log = [qs_item.consumed_units for qs_item in qs]
            total_consumed_units = sum(log)

            extra_consumed, free = self._get_extra_consumed_units_during_trial(
                metered_feature, total_consumed_units)

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

    def _add_plan_value(self, start_date, end_date, invoice=None,
                        proforma=None):
        """
        Adds to the document the value of the plan.
        """

        prorated, percent = self._get_proration_status_and_percent(start_date,
                                                                   end_date)

        context = self._build_entry_context({
            'name': self.plan.name,
            'unit': self.plan.interval,
            'product_code': self.plan.product_code,
            'start_date': start_date,
            'end_date': end_date,
            'prorated': prorated,
            'proration_percentage': percent,
            'context': 'plan'
        })
        description = self._entry_description(context)

        # Get the plan's prorated value
        plan_price = self.plan.amount * percent

        unit = self._entry_unit(context)

        return DocumentEntry.objects.create(
            invoice=invoice, proforma=proforma, description=description,
            unit=unit, unit_price=plan_price, quantity=Decimal('1.00'),
            product_code=self.plan.product_code, prorated=prorated,
            start_date=start_date, end_date=end_date
        ).total

    def _get_consumed_units(self, metered_feature, proration_percent,
                            start_date, end_date):
        included_units = (proration_percent * metered_feature.included_units)

        qs = self.mf_log_entries.filter(metered_feature=metered_feature,
                                        start_date__gte=start_date,
                                        end_date__lte=end_date)
        log = [qs_item.consumed_units for qs_item in qs]
        total_consumed_units = reduce(lambda x, y: x + y, log, 0)

        if total_consumed_units > included_units:
            return total_consumed_units - included_units
        return 0

    def _add_mfs(self, start_date, end_date, invoice=None, proforma=None):
        prorated, percent = self._get_proration_status_and_percent(start_date,
                                                                   end_date)

        context = self._build_entry_context({
            'name': self.plan.name,
            'unit': self.plan.interval,
            'product_code': self.plan.product_code,
            'start_date': start_date,
            'end_date': end_date,
            'prorated': prorated,
            'proration_percentage': percent,
            'context': 'metered-feature'
        })

        mfs_total = Decimal('0.00')
        for metered_feature in self.plan.metered_features.all():
            consumed_units = self._get_consumed_units(
                metered_feature, percent, start_date, end_date)

            context.update({'metered_feature': metered_feature,
                            'unit': metered_feature.unit,
                            'name': metered_feature.name,
                            'product_code': metered_feature.product_code})

            description = self._entry_description(context)
            unit = self._entry_unit(context)

            mf = DocumentEntry.objects.create(
                invoice=invoice, proforma=proforma,
                description=description, unit=unit,
                quantity=consumed_units, prorated=prorated,
                unit_price=metered_feature.price_per_unit,
                product_code=metered_feature.product_code,
                start_date=start_date, end_date=end_date
            )

            mfs_total += mf.total

        return mfs_total

    def _get_proration_status_and_percent(self, start_date, end_date):
        """
        Returns the proration percent (how much of the interval will be billed)
        and the status (if the subscription is prorated or not).

        :returns: a tuple containing (Decimal(percent), status) where status
            can be one of [True, False]. The decimal value will from the
            interval [0.00; 1.00].
        :rtype: tuple
        """

        first_day_of_month = date(start_date.year, start_date.month, 1)
        last_day_index = calendar.monthrange(start_date.year,
                                             start_date.month)[1]
        last_day_of_month = date(start_date.year, start_date.month,
                                 last_day_index)

        if start_date == first_day_of_month and end_date == last_day_of_month:
            return False, Decimal('1.0000')
        else:
            days_in_full_interval = (last_day_of_month - first_day_of_month).days + 1
            days_in_interval = (end_date - start_date).days + 1
            percent = 1.0 * days_in_interval / days_in_full_interval
            percent = Decimal(percent).quantize(Decimal('0.0000'))

            return True, percent

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
        return u'%s (%s)' % (self.customer, self.plan)


@python_2_unicode_compatible
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
