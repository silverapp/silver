import datetime
from datetime import datetime as dt
from decimal import Decimal
import calendar

import jsonfield
from django_fsm import FSMField, transition
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.db import models
from django.template import TemplateDoesNotExist
from django.template.loader import (get_template, render_to_string)
from dateutil.relativedelta import *
from dateutil import rrule
from model_utils import Choices


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
        'Plan',
        help_text='The plan the customer is subscribed to.'
    )
    description = models.CharField(max_length=1024, blank=True, null=True)
    customer = models.ForeignKey(
        'Customer', related_name='subscriptions',
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
        max_length=128, blank=True, null=True,
        help_text="The subscription's reference in an external system."
    )

    state = FSMField(
        choices=STATE_CHOICES, max_length=12, default=STATES.INACTIVE,
        protected=True, help_text='The state the subscription is in.'
    )
    meta = jsonfield.JSONField(blank=True, null=True)

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

    def _current_start_date(self, reference_date=None, ignore_trial=None,
                            granulate=None):
        ignore_trial_default = False
        granulate_default = False

        ignore_trial = ignore_trial_default or ignore_trial
        granulate = granulate_default or granulate

        interval_count = 1 if granulate else self.plan.interval_count

        if reference_date is None:
            reference_date = timezone.now().date()

        if not self.start_date or reference_date < self.start_date:
            return None

        if (ignore_trial or not self.trial_end) \
                or self.trial_end >= reference_date:
            relative_start_date = self.start_date
        else:
            relative_start_date = self.trial_end + datetime.timedelta(days=1)

        # we calculate a fake (intermediary) start date depending on the
        # interval type, for the purposes of alignment to a specific day
        bymonth = bymonthday = byweekday = None
        if self.plan.interval == self.plan.INTERVALS.MONTH:
            bymonthday = 1  # first day of the month
        elif self.plan.interval == self.plan.INTERVALS.WEEK:
            byweekday = 0  # first day of the week (Monday)
        elif self.plan.interval == self.plan.INTERVALS.YEAR:
            # first day of the first month (1 Jan)
            bymonth = 1
            bymonthday = 1

        fake_initial_date = list(
            rrule.rrule(self._INTERVALS_CODES[self.plan.interval],
                  count=1,
                  bymonth=bymonth,
                  bymonthday=bymonthday,
                  byweekday=byweekday,
                  dtstart=relative_start_date)
        )[-1].date()

        if fake_initial_date > reference_date:
            fake_initial_date = relative_start_date

        dates = list(
            rrule.rrule(self._INTERVALS_CODES[self.plan.interval],
                  dtstart=fake_initial_date,
                  interval=interval_count,
                  until=reference_date)
        )

        return fake_initial_date if not dates else dates[-1].date()

    def _current_end_date(self, reference_date=None, ignore_trial=None,
                          granulate=None):
        ignore_trial_default = False
        granulate_default = False

        ignore_trial = ignore_trial_default or ignore_trial
        granulate = granulate_default or granulate

        if reference_date is None:
            reference_date = timezone.now().date()

        end_date = None
        _current_start_date = self._current_start_date(reference_date,
                                                       ignore_trial, granulate)

        # we need a current start date in order to compute a current end date
        if not _current_start_date:
            return None

        # we calculate a fake (intermediary) end date depending on the interval
        # type, for the purposes of alignment to a specific day
        bymonth = bymonthday = byweekday = None
        count = 1
        interval_count = 1
        if self.plan.interval == self.plan.INTERVALS.MONTH and\
           _current_start_date.day != 1:
            bymonthday = 1  # first day of the month
        elif self.plan.interval == self.plan.INTERVALS.WEEK and\
                _current_start_date.weekday() != 0:
            byweekday = 0  # first day of the week (Monday)
        elif (self.plan.interval == self.plan.INTERVALS.YEAR and
              _current_start_date.month != 1 and _current_start_date.day != 1):
            # first day of the first month (1 Jan)
            bymonth = 1
            bymonthday = 1
        else:
            count = 2
            if not granulate:
                interval_count = self.plan.interval_count

        fake_end_date = list(
            rrule.rrule(self._INTERVALS_CODES[self.plan.interval],
                  interval=interval_count,
                  count=count,
                  bymonth=bymonth,
                  bymonthday=bymonthday,
                  byweekday=byweekday,
                  dtstart=_current_start_date)
        )[-1].date() - datetime.timedelta(days=1)

        # if the trial_end date is set and we're not ignoring it
        if self.trial_end and not ignore_trial:
            # if the fake_end_date is past the trial_end date
            if (fake_end_date and
                    fake_end_date > self.trial_end >= reference_date):
                fake_end_date = self.trial_end

        # check if the fake_end_date is not past the ended_at date
        if fake_end_date:
            if self.ended_at:
                if self.ended_at < fake_end_date:
                    end_date = self.ended_at
            else:
                end_date = fake_end_date
            return end_date
        return self.ended_at or None

    @property
    def current_start_date(self):
        return self._current_start_date(ignore_trial=True, granulate=False)

    @property
    def current_end_date(self):
        return self._current_end_date(ignore_trial=True, granulate=False)

    def bucket_start_date(self, reference_date=None):
        return self._current_start_date(reference_date=reference_date,
                                        ignore_trial=False, granulate=True)

    def bucket_end_date(self, reference_date=None):
        return self._current_end_date(reference_date=reference_date,
                                      ignore_trial=False, granulate=True)

    def updateable_buckets(self):
        if self.state in ['ended', 'inactive']:
            return None
        buckets = list()
        start_date = self.bucket_start_date()
        end_date = self.bucket_end_date()
        if start_date is None or end_date is None:
            return buckets
        buckets.append({'start_date': start_date, 'end_date': end_date})

        generate_after = datetime.timedelta(seconds=self.plan.generate_after)
        while (timezone.now() - generate_after
                < dt.combine(start_date, dt.min.time()).replace(
                    tzinfo=timezone.get_current_timezone())):
            end_date = start_date - datetime.timedelta(days=1)
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

    def should_be_billed(self, date):
        if date < self.start_date:
            msg = 'Billing date has to be >= than subscription\'s start date.'
            raise ValueError(msg)

        generate_after = datetime.timedelta(seconds=self.plan.generate_after)
        ONE_DAY = datetime.timedelta(days=1)

        if self.state == self.STATES.CANCELED:
            if date >= (self.cancel_date + generate_after):
                if self._has_existing_customer_with_consolidated_billing:
                    if self.cancel_date.day == 1:
                        # If the subscription was canceled at
                        # `end_of_billing_cycle` the cancel day will be set as
                        # the first day of the next month (see
                        # `Subscription.cancel()`)
                        # Also, if it was canceled `now`, in the 1st day of the
                        # month, it should be billed too
                        interval_end = self.cancel_date
                    else:
                        # If cancel_date.day != 1 => it was definitely canceled
                        # `now` (remember that the cancel_date is set
                        # automatically as the first day of the next month) =>
                        # if the customer has consolidated billing it should
                        # be billed only the next month => interval_end is taken
                        # as the end of month when it was canceled
                        interval_end = list(
                            rrule.rrule(
                                rrule.MONTHLY,
                                count=1,
                                bymonthday=-1,
                                dtstart=self.cancel_date)
                        )[-1].date()
                else:
                    # The customer either does not have consolidated billing
                    # or it does not have any other active subscriptions
                    # => it should be billed now since billing date >= cancel_date
                    return True
            else:
                # date < cancel_date => don't charge the subscription
                return False

            return date >= interval_end + ONE_DAY + generate_after

        if self.state != self.STATES.ACTIVE:
            # It was not canceled and it is not active either => don't bill it.
            return False

        if self.is_billed_first_time:
            if not self.trial_end:
                # The subscription does not have a trial => it should
                # be billed right after being activated. However, if the
                # customer has consolidated billing and he has subscriptions
                # the subscription should be billed only at the next
                # billing cycle
                if self._has_existing_customer_with_consolidated_billing:
                    interval_end = self.bucket_end_date(
                        reference_date=self.start_date
                    )
                else:
                    # The customer either does not have consolidated billing
                    # or it does not have any other active subscriptions
                    # => it should be billed right now, after starting the
                    # subscription
                    return True
            else:
                if self._has_existing_customer_with_consolidated_billing:
                    # Is billed first time and has consolidated billing => it
                    # should be billed only next month no matter if the trial
                    # spans over multiple months or not

                    # Get the end of the month when the subscription was
                    # activated
                    interval_end = list(
                        rrule.rrule(
                            rrule.MONTHLY,
                            count=1,
                            bymonthday=-1,
                            dtstart=self.start_date)
                    )[-1].date()
                else:
                    # The customer does not have consolidated billing =>
                    # the subscription should be billed after trial_end
                    # or if the trial spans over multiple months at the end of
                    # first month. The date (either the end of the month or
                    # trial_end given by Subscription.bucket_end_date.
                    interval_end = self.bucket_end_date(
                        reference_date=self.start_date
                    )
        else:
            last_billing_date = self.last_billing_date
            if self.on_trial(last_billing_date):
                if self._has_existing_customer_with_consolidated_billing:
                    # If the customer has consolidated billing the subscription
                    # should be charged only next month

                    # Get the end of the month when it was last billed
                    interval_end = list(
                        rrule.rrule(
                            rrule.MONTHLY,
                            count=1,
                            bymonthday=-1,
                            dtstart=last_billing_date)
                    )[-1].date()
                else:
                    # If at the last billing the subscription was on trial
                    # => trial_end could be either this month or sometimes in
                    # the future => if the customer does not have consolidated
                    # billing it should be billed either after the trial_end (if
                    # trial_end is this month or at the end of the month.
                    # trial_end or end of the month is returned by
                    # `Subscription.bucket_end_date`
                    interval_end = self.bucket_end_date(
                        reference_date=last_billing_date
                    )
            else:
                # last time it was billed the subscription was not on trial
                # => it should be billed at the beginning of the next month
                # => get the end of the bucket
                interval_end = self.bucket_end_date(
                    reference_date=last_billing_date
                )

        return date >= interval_end + ONE_DAY + generate_after

    @property
    def _has_existing_customer_with_consolidated_billing(self):
        return (
            self.customer.consolidated_billing and
            self.customer.subscriptions.filter(state=self.STATES.ACTIVE).count() > 1
        )

    @property
    def is_billed_first_time(self):
        return self.billing_log_entries.all().count() == 0

    @property
    def last_billing_date(self):
        try:
            return self.billing_log_entries.all()[:1].get().billing_date
        except BillingLog.DoesNotExist:
            # It should never get here.
            return None

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

        if trial_end_date:
            self.trial_end = max(self.start_date, trial_end_date)
        else:
            if self.trial_end:
                if self.trial_end < self.start_date:
                    self.trial_end = None
            elif self.plan.trial_period_days > 0:
                self.trial_end = self.start_date + datetime.timedelta(
                    days=self.plan.trial_period_days - 1)

    @transition(field=state, source=STATES.ACTIVE, target=STATES.CANCELED)
    def cancel(self, when):
        now = timezone.now().date()
        bsd = self.bucket_start_date()
        bed = self.bucket_end_date()

        if when == self.CANCEL_OPTIONS.END_OF_BILLING_CYCLE:
            ONE_DAY = datetime.timedelta(days=1)
            if self.is_on_trial:
                bucket_after_trial = self.bucket_end_date(
                    reference_date=self.trial_end + ONE_DAY)
                # After trial_end comes a prorated paid period. The cancel_date
                # should be one day after the end of the prorated paid period.
                self.cancel_date = bucket_after_trial + ONE_DAY
            else:
                self.cancel_date = self.current_end_date + ONE_DAY
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

    def add_total_value_to_document(self, billing_date, invoice=None,
                                    proforma=None):
        """
        Adds the total value of the subscription (value(plan) + value(consumed
        metered features)) to the document.
        """

        ONE_DAY = datetime.timedelta(days=1)

        if self.is_billed_first_time:
            if not self.trial_end:  # has no trial
                if billing_date.month in [self.start_date.month,
                                          self.start_date.month + 1]:
                    # The same month or the next one as the start_date

                    # Generate first invoice, when the subscription starts
                    # => add the prorated value of the plan for the current month
                    end_date = self._get_interval_end_date(date=self.start_date)
                    self._add_plan_value(start_date=self.start_date,
                                         end_date=end_date,
                                         invoice=invoice, proforma=proforma)

                    if (self.state == self.STATES.CANCELED and
                        self.cancel_date.month == self.start_date.month and
                        self.cancel_date == billing_date.month
                    ):
                        # It was canceled the same month it started, with `now`
                        # option and since it got here (by permissions of
                        # Subscription.should_be_billed) => the customer does
                        # not have consolidated billing => add the mfs as this
                        # is the last subscription of the customer and (s)he
                        # is probably leaving the service.
                        self._add_mfs(start_date=self.start_date,
                                      end_date=end_date,
                                      invoice=invoice, proforma=proforma)

                    if billing_date.month == self.start_date.month + 1:
                        # If it gets here => a new subscription, with no trial
                        # and the customer has other subscriptions => it's
                        # an old customer.
                        # Add consumed mfs from last month
                        self._add_mfs(start_date=self.start_date,
                                      end_date=end_date,
                                      invoice=invoice, proforma=proforma)

                        if self.state == self.STATES.ACTIVE:
                            # If the subscription is still active, add the
                            # plan's value for the month ahead
                            bsd = self.bucket_start_date(
                                reference_date=billing_date)
                            bed = self.bucket_end_date(
                                reference_date=billing_date)
                            self._add_plan_value(
                                start_date=bsd, end_date=bed,
                                invoice=invoice, proforma=proforma)
            elif self.on_trial(billing_date):
                # Next month after the subscription has started with trial
                # spanning over >=2 months
                end_date = self._get_interval_end_date(date=self.start_date)
                self._add_trial_value(start_date=self.start_date,
                                      end_date=end_date,
                                      invoice=invoice, proforma=proforma)
            else:
                # Billed first time, right after trial end

                # Is billed right after trial in the same month as start_date
                # => add the trial value and the prorated value for the rest
                # of the month

                # Add the value of the plan + the value of the consumed mfs
                # during the trial
                end_date = self._get_interval_end_date(date=self.start_date)
                self._add_trial_value(start_date=self.start_date,
                                      end_date=end_date,
                                      invoice=invoice, proforma=proforma)

                first_day_after_trial = self.trial_end + ONE_DAY
                # If it got here (by permission of `should_be_billed()`
                # => it has to be either ACTIVE or CANCELED
                end_date = None
                if self.state == self.STATES.ACTIVE:
                    # Add the value for the rest of the month if the
                    # subscription is still active
                    end_date = self.bucket_end_date(
                        reference_date=first_day_after_trial)
                elif self.state == self.STATES.CANCELED:
                    # The subscription was canceled after the trial, during
                    # the prorated period of the month => add the value
                    # only between trial_end -> cancel_date
                    if self.cancel_date >= first_day_after_trial:
                        end_date = self.cancel_date

                if first_day_after_trial.month == self.trial_end.month:
                    # Add the prorated value of the plan between
                    # trial_end -> end_of_month only if the first day after
                    # trial belongs to the same month as the trial end.
                    # Exception e.g.: trial_end = 31.08.2015.
                    # trial_end + ONE_DAY = 1.09.2015 => don't add any prorated
                    # value.

                    if (self.state == self.STATES.ACTIVE or
                        (self.state == self.STATES.CANCELED and
                         self.cancel_date >= self.trial_end)
                    ):
                        # Add the prorated plan value for trial_end -> end_of_month
                        # if the subscription is active or if it was canceled
                        # between trial_end -> end_of_month.
                        # note: it could have been canceled before trial_end
                        # and in that case the value does not have to be added
                        self._add_plan_value(start_date=first_day_after_trial,
                                            end_date=end_date,
                                            invoice=invoice, proforma=proforma)

                        if billing_date.month == self.start_date.month + 1:
                            # It's the next month after the subscription start
                            # and there was a prorated period between trial_end ->
                            # end_of_month => add the consumed metered features
                            # from that period.
                            self._add_mfs(start_date=first_day_after_trial,
                                          end_date=end_date,
                                          invoice=invoice, proforma=proforma)

                if (self.state == self.STATES.ACTIVE and
                    billing_date.month == self.start_date.month + 1
                ):
                    # It's billed next month after the start date and it is
                    # still active => add the prorated value for the next month
                    bsd = self.bucket_start_date(reference_date=billing_date)
                    bed = self.bucket_end_date(reference_date=billing_date)
                    self._add_plan_value(start_date=bsd, end_date=bed,
                                         invoice=invoice, proforma=proforma)
        else:
            last_billing_date = self.last_billing_date
            if (self.trial_end and
                (self.trial_end.month == billing_date.month or
                 self.trial_end.month == billing_date.month - 1) and
                last_billing_date < self.trial_end
            ):
                # It has/had a trial which ends this month or it ended last
                # month and it has been billed before
                # => expect the following items:
                #   * the remaining trial value since last billing
                #   * the value of the prorated subscription
                #   * the value of the subscription ahead
                # note: it will get here only after the trial has ended
                # We test if trial_end was this month or the previous one.

                # Add trial value
                # The end_date will be either the normal end_date of the
                # bucket or the cancel_date (if the subscription is canceled)
                bsd = self.bucket_start_date(reference_date=last_billing_date)
                bed = self.bucket_end_date(reference_date=last_billing_date)
                if self.state == self.STATES.CANCELED:
                    if bsd <= self.cancel_date <= bed:
                        # Was scheduled for canceling sometimes during the
                        # trial period
                        bed = self.cancel_date

                self._add_trial_value(start_date=bsd, end_date=bed,
                                      invoice=invoice, proforma=proforma)

                # Add the plan's value for the period after the trial
                # The end_date will be either the normal end_date of the
                # bucket or the cancel_date (if the subscription is canceled)
                first_day_after_trial = self.trial_end + ONE_DAY

                if first_day_after_trial.month == self.trial_end.month:
                    # The same month as the trial end => add prorated value of the
                    # subscription between first_day_after_trial and end of the
                    # month
                    bsd = self.bucket_start_date(
                        reference_date=first_day_after_trial)
                    bed = self.bucket_end_date(
                        reference_date=first_day_after_trial)
                    if self.state == self.STATES.CANCELED:
                        if bsd <= self.cancel_date <= bed:
                            bed = self.cancel_date

                    if (self.state == self.STATES.ACTIVE or
                        self.cancel_date >= self.trial_end
                    ):
                        # Add the prorated value only if the subscription is still
                        # active or it was canceled during the period right after
                        # the trial. If it was canceled during the trial, skip
                        # adding the mfs, as there was no active period after
                        # trial_end
                        self._add_plan_value(start_date=bsd, end_date=bed,
                                             invoice=invoice, proforma=proforma)

                        if billing_date.month == first_day_after_trial.month + 1:
                            # If there was a period of paid subscription between
                            # trial_end -> last_month_end=> add the consumed mfs
                            # for that period.
                            # Note: the bsd and bed that were previously
                            # computed are being used
                            self._add_mfs(start_date=bsd, end_date=bed,
                                          invoice=invoice, proforma=proforma)

                # The subscription was not canceled and we bill it the
                # next month after the trial end => add the value of the
                # subscription for the next month
                if (self.state == self.STATES.ACTIVE and
                    billing_date.month == self.trial_end.month + 1
                ):
                    # It's the next month after the trial end => add the value
                    # for the month ahead
                    bsd = self.bucket_start_date(reference_date=billing_date)
                    bed = self.bucket_end_date(reference_date=billing_date)
                    self._add_plan_value(start_date=bsd, end_date=bed,
                                        invoice=invoice, proforma=proforma)

            else:
                # This is the normal case of a subscription which was billed
                # sometimes at the beginning of last month or it's the next
                # month after the trial_end of a subscription whose customer
                # does not have consolidated billing => the subscription was
                # billed after trial_end.

                # Add mfs for the last month or part of month
                bsd = self.bucket_start_date(reference_date=last_billing_date)
                bed = self.bucket_end_date(reference_date=last_billing_date)
                self._add_mfs(start_date=bsd, end_date=bed,
                              invoice=invoice, proforma=proforma)

                if self.state == self.STATES.ACTIVE:
                    # Add the plan's value for the month ahead
                    bsd = self.bucket_start_date(reference_date=billing_date)
                    bed = self.bucket_end_date(reference_date=billing_date)

                    self._add_plan_value(start_date=bsd, end_date=bed,
                                         invoice=invoice, proforma=proforma)

        BillingLog.objects.create(subscription=self, invoice=invoice,
                                  proforma=proforma, billing_date=billing_date)

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
            start_date=start_date, end_date=end_date)

        context.update({
            'context': 'plan-trial-discount'
        })

        description = self._entry_description(context)

        # Add plan with negative value
        DocumentEntry.objects.create(
            invoice=invoice, proforma=proforma, description=description,
            unit=unit, unit_price=-plan_price, quantity=Decimal('1.00'),
            product_code=self.plan.product_code, prorated=prorated,
            start_date=start_date, end_date=end_date)

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
            # The following part tries so handle the case when the trial
            # spans over 2 months and the subscription has been already billed
            # once => this month it is still on trial but it only
            # has remaining = consumed_last_cycle - included_during_trial
            last_log_entry = self.billing_log_entries.all()[0]
            if last_log_entry.proforma:
                qs = last_log_entry.proforma.proforma_entries.filter(
                    product_code=metered_feature.product_code)
            else:
                qs = last_log_entry.invoice.invoice_entries.filter(
                    product_code=metered_feature.product_code)

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
                    description_template_path, context)

                DocumentEntry.objects.create(
                    invoice=invoice, proforma=proforma,
                    description=description, unit=unit,
                    quantity=charged_units, prorated=prorated,
                    unit_price=metered_feature.price_per_unit,
                    product_code=metered_feature.product_code,
                    start_date=start_date, end_date=end_date)

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

        DocumentEntry.objects.create(
            invoice=invoice, proforma=proforma, description=description,
            unit=unit, unit_price=plan_price, quantity=Decimal('1.00'),
            product_code=self.plan.product_code, prorated=prorated,
            start_date=start_date, end_date=end_date
        )

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

        for metered_feature in self.plan.metered_features.all():
            consumed_units = self._get_consumed_units(
                metered_feature, percent, start_date, end_date)

            context.update({'metered_feature': metered_feature,
                            'unit': metered_feature.unit,
                            'name': metered_feature.name,
                            'product_code': metered_feature.product_code})

            description = self._entry_description(context)
            unit = self._entry_unit(context)

            DocumentEntry.objects.create(
                invoice=invoice, proforma=proforma,
                description=description, unit=unit,
                quantity=consumed_units, prorated=prorated,
                unit_price=metered_feature.price_per_unit,
                product_code=metered_feature.product_code,
                start_date=start_date, end_date=end_date)

    def _get_proration_status_and_percent(self, start_date, end_date):
        """
        Returns the proration percent (how much of the interval will be billed)
        and the status (if the subscription is prorated or not).

        :returns: a tuple containing (Decimal(percent), status) where status
            can be one of [True, False]. The decimal value will from the
            interval [0.00; 1.00].
        :rtype: tuple
        """

        first_day_of_month = datetime.date(start_date.year, start_date.month, 1)
        last_day_index = calendar.monthrange(start_date.year,
                                             start_date.month)[1]
        last_day_of_month = datetime.date(start_date.year, start_date.month,
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

    def __unicode__(self):
        return u'%s (%s)' % (self.customer, self.plan)
