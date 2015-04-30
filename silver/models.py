import datetime
from datetime import datetime as dt
from decimal import Decimal
from django.core.validators import MinValueValidator
from django.template import TemplateDoesNotExist
from django.template.loader import select_template, get_template, \
    render_to_string

import jsonfield
from django_fsm import FSMField, transition, TransitionNotAllowed
from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
from django.core.files.base import ContentFile
from django.http import HttpResponse
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.utils.module_loading import import_string
from django.utils.text import slugify
from django_xhtml2pdf.utils import generate_pdf_template_object
from django.db import models
from django.db.models import Max
from django.conf import settings
from django.db.models.signals import pre_delete, pre_save
from django.dispatch.dispatcher import receiver
from international.models import countries, currencies
from livefield.models import LiveModel
from dateutil.relativedelta import *
from dateutil.rrule import *
from pyvat import is_vat_number_format_valid

from silver.utils import get_object_or_None


UPDATE_TYPES = (
    ('absolute', 'Absolute'),
    ('relative', 'Relative')
)

_INTERVALS_CODES = {
    'year': 0,
    'month': 1,
    'week': 2,
    'day': 3
}

PAYMENT_DUE_DAYS = getattr(settings, 'SILVER_DEFAULT_DUE_DAYS', 5)

_storage = getattr(settings, 'SILVER_DOCUMENT_STORAGE', None)
if _storage:
    _storage_klass = import_string(_storage[0])
    _storage = _storage_klass(*_storage[1], **_storage[2])


def documents_pdf_path(document, filename):
    path = '{prefix}{company}/{doc_name}/{date}/{filename}'.format(
        company=slugify(unicode(
            document.provider.company or document.provider.name)),
        date=document.issue_date.strftime('%Y/%m'),
        doc_name=('%ss' % document.__class__.__name__).lower(),
        prefix=getattr(settings, 'SILVER_DOCUMENT_PREFIX', ''),
        filename=filename)
    return path


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


class UnsavedForeignKey(models.ForeignKey):
    allow_unsaved_instance_assignment = True


class Plan(models.Model):
    INTERVALS = (
        ('day', 'Day'),
        ('week', 'Week'),
        ('month', 'Month'),
        ('year', 'Year')
    )

    name = models.CharField(
        max_length=200, help_text='Display name of the plan.'
    )
    interval = models.CharField(
        choices=INTERVALS, max_length=12, default=INTERVALS[2][0],
        help_text='The frequency with which a subscription should be billed.'
    )
    interval_count = models.PositiveIntegerField(
        help_text='The number of intervals between each subscription billing'
    )
    amount = models.DecimalField(
        max_digits=8, decimal_places=2, validators=[MinValueValidator(0.0)],
        help_text='The amount in the specified currency to be charged on the '
                  'interval specified.'
    )
    currency = models.CharField(
        choices=currencies, max_length=4, default='USD',
        help_text='The currency in which the subscription will be charged.'
    )
    trial_period_days = models.PositiveIntegerField(
        null=True,
        help_text='Number of trial period days granted when subscribing a '
                  'customer to this plan.'
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
    enabled = models.BooleanField(default=True,
                                  help_text='Whether to accept subscriptions.')
    private = models.BooleanField(default=False,
                                  help_text='Indicates if a plan is private.')
    product_code = models.ForeignKey(
        'ProductCode', help_text='The product code for this plan.'
    )
    provider = models.ForeignKey(
        'Provider', related_name='plans',
        help_text='The provider which provides the plan.'
    )

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

    def __unicode__(self):
        return self.name

    @property
    def provider_flow(self):
        return self.provider.flow


class MeteredFeature(models.Model):
    name = models.CharField(
        max_length=200,
        help_text='The feature display name.'
    )
    unit = models.CharField(max_length=20)
    price_per_unit = models.DecimalField(
        max_digits=8, decimal_places=2, validators=[MinValueValidator(0.0)],
        help_text='The price per unit.',
    )
    included_units = models.DecimalField(
        max_digits=19, decimal_places=2, validators=[MinValueValidator(0.0)],
        help_text='The number of included units per plan interval.'
    )
    included_units_during_trial = models.DecimalField(
        max_digits=19, decimal_places=2, validators=[MinValueValidator(0.0)],
        blank=True, null=True,
        help_text='The number of included units during the trial period.'
    )
    product_code = UnsavedForeignKey(
        'ProductCode', help_text='The product code for this plan.'
    )

    def __unicode__(self):
        return self.name


class MeteredFeatureUnitsLog(models.Model):
    metered_feature = models.ForeignKey('MeteredFeature', related_name='consumed')
    subscription = models.ForeignKey('Subscription', related_name='mf_log_entries')
    consumed_units = models.DecimalField(max_digits=19, decimal_places=2,
                                         validators=[MinValueValidator(0.0)])
    start_date = models.DateField(editable=False)
    end_date = models.DateField(editable=False)

    class Meta:
        unique_together = ('metered_feature', 'subscription', 'start_date',
                           'end_date')

    def clean(self):
        super(MeteredFeatureUnitsLog, self).clean()
        if self.subscription.state in ['ended', 'inactive']:
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

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.id:
            if not self.start_date:
                self.start_date = self.subscription.bucket_start_date()
            if not self.end_date:
                self.end_date = self.subscription.bucket_end_date()
            super(MeteredFeatureUnitsLog, self).save(force_insert, force_update,
                                                     using, update_fields)

        if self.id:
            update_fields = []
            for field in self._meta.fields:
                if field.name != 'metered_feature' and field.name != 'id':
                    update_fields.append(field.name)
            super(MeteredFeatureUnitsLog, self).save(
                update_fields=update_fields)

    def __unicode__(self):
        return self.metered_feature.name


class Subscription(models.Model):
    STATES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('canceled', 'Canceled'),
        ('ended', 'Ended')
    )

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
    ended_at = models.DateField(
        blank=True, null=True,
        help_text='The date when the subscription ended.'
    )
    reference = models.CharField(
        max_length=128, blank=True, null=True,
        help_text="The subscription's reference in an external system."
    )

    state = FSMField(
        choices=STATES, max_length=12, default=STATES[1][0], protected=True,
        help_text='The state the subscription is in.'
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
            if self.state not in ['canceled', 'ended']:
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
        if self.plan.interval == 'month':
            bymonthday = 1  # first day of the month
        elif self.plan.interval == 'week':
            byweekday = 0  # first day of the week (Monday)
        elif self.plan.interval == 'year':
            # first day of the first month (1 Jan)
            bymonth = 1
            bymonthday = 1

        fake_initial_date = list(
            rrule(_INTERVALS_CODES[self.plan.interval],
                  count=1,
                  bymonth=bymonth,
                  bymonthday=bymonthday,
                  byweekday=byweekday,
                  dtstart=relative_start_date)
        )[-1].date()

        if fake_initial_date > reference_date:
            fake_initial_date = relative_start_date

        dates = list(
            rrule(_INTERVALS_CODES[self.plan.interval],
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
        if self.plan.interval == 'month' and _current_start_date.day != 1:
            bymonthday = 1  # first day of the month
        elif self.plan.interval == 'week' and _current_start_date.weekday() != 0:
            byweekday = 0  # first day of the week (Monday)
        elif (self.plan.interval == 'year' and _current_start_date.month != 1
              and _current_start_date.day != 1):
            # first day of the first month (1 Jan)
            bymonth = 1
            bymonthday = 1
        else:
            count = 2
            if not granulate:
                interval_count = self.plan.interval_count

        fake_end_date = list(
            rrule(_INTERVALS_CODES[self.plan.interval],
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
        if self.state == 'active' and self.trial_end:
            return timezone.now().date() <= self.trial_end
        return False

    def was_on_trial(self, date):
        if self.trial_end:
            return date <= self.trial_end
        return False

    def should_be_billed(self, date):
        if self.state == 'canceled':
            return True

        generate_after = datetime.timedelta(seconds=self.plan.generate_after)
        if self.is_billed_first_time:
            interval_end = self._current_end_date(reference_date=self.start_date)
        else:
            interval_end = self._current_end_date(reference_date=self.last_billing_date)
        return date >= interval_end + generate_after

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

    @transition(field=state, source=['inactive', 'canceled'], target='active')
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

    @transition(field=state, source=['active'], target='canceled')
    def cancel(self):
        canceled_at_date = timezone.now().date()
        bsd = self.bucket_start_date()
        bed = self.bucket_end_date()
        for metered_feature in self.plan.metered_features.all():
            log = MeteredFeatureUnitsLog.objects.filter(
                start_date=bsd,
                end_date=bed,
                metered_feature=metered_feature.pk,
                subscription=self.pk
            ).first()
            if log:
                log.end_date = canceled_at_date
                log.save()

        if self.trial_end and self.trial_end > canceled_at_date:
            self.trial_end = canceled_at_date
            self.save()

    @transition(field=state, source='canceled', target='ended')
    def end(self):
        self.ended_at = timezone.now().date()

    def _add_trial_value(self, start_date, end_date, invoice=None,
                         proforma=None):
        self._add_plan_trial(start_date=start_date, end_date=end_date,
                             invoice=invoice, proforma=proforma)
        self._add_mfs_for_trial(start_date=start_date, end_date=end_date,
                                invoice=invoice, proforma=proforma)

    def _add_non_trial_value(self, start_date, end_date, invoice=None,
                             proforma=None):
        self._add_plan_value(start_date=start_date, end_date=end_date,
                             invoice=invoice, proforma=proforma)
        self._add_mfs(start_date, end_date, invoice=invoice, proforma=proforma)

    def add_total_value_to_document(self, billing_date, invoice=None,
                                    proforma=None):
        """
        Adds the total value of the subscription (value(plan) + value(consumed
        metered features)) to the document.
        """

        if self.is_billed_first_time:
            if self.was_on_trial(billing_date):
                self._add_trial_value(self.start_date, billing_date,
                                      invoice=invoice, proforma=proforma)
            else:
                self._add_trial_value(self.start_date, self.trial_end,
                                      invoice=invoice, proforma=proforma)

                trial_end = self.trial_end + datetime.timedelta(days=1)
                self._add_non_trial_value(trial_end, billing_date,
                                          invoice=invoice, proforma=proforma)
        else:
            last_billing_date = self.last_billing_date + datetime.timedelta(days=1)
            if self.was_on_trial(last_billing_date):
                self._add_trial_value(last_billing_date, self.trial_end,
                                      invoice=invoice, proforma=proforma)

                trial_end = self.trial_end + datetime.timedelta(days=1)
                self._add_non_trial_value(trial_end, billing_date,
                                          invoice=invoice, proforma=proforma)
            else:
                self._add_non_trial_value(last_billing_date, billing_date,
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

        context = {
            'name': self.plan.name,
            'subscription': self,
            'plan': self.plan,
            'provider': self.plan.provider,
            'customer': self.customer,
            'product_code': self.plan.product_code,
            'start_date': start_date,
            'end_date': end_date,
            'prorated': prorated,
            'proration_percentage': percent,
            'context': 'plan-trial'
        }

        unit_template_path = field_template_path(
            field='entry_unit', provider=self.plan.provider.billing_name
        )

        unit = render_to_string(unit_template_path, context)

        description_template_path = field_template_path(
            field='entry_description', provider=self.plan.provider.billing_name
        )

        description = render_to_string(description_template_path, context)

        # Add plan with positive value
        DocumentEntry.objects.create(
            invoice=invoice, proforma=proforma, description=description,
            unit=unit, unit_price=plan_price, quantity=Decimal('1.00'),
            product_code=self.plan.product_code, prorated=prorated,
            start_date=start_date, end_date=end_date)

        context['context'] = 'plan-trial-discount'

        description = render_to_string(description_template_path, context)

        # Add plan with negative value
        DocumentEntry.objects.create(
            invoice=invoice, proforma=proforma, description=description,
            unit=unit, unit_price=-plan_price, quantity=Decimal('1.00'),
            product_code=self.plan.product_code, prorated=prorated,
            start_date=start_date, end_date=end_date)

    def _get_consumed_units_during_trial(self, metered_feature, consumed_units):
        if metered_feature.included_units_during_trial:
            if consumed_units > metered_feature.included_units_during_trial:
                return consumed_units - metered_feature.included_units_during_trial
        return 0

    def _add_mfs_for_trial(self, start_date, end_date, invoice=None,
                           proforma=None):

        prorated, percent = self._get_proration_status_and_percent(start_date,
                                                                   end_date)
        context = {
            'subscription': self,
            'plan': self.plan,
            'provider': self.plan.provider,
            'customer': self.customer,
            'product_code': self.plan.product_code,
            'start_date': start_date,
            'end_date': end_date,
            'prorated': prorated,
            'proration_percentage': percent,
            'context': 'mfs-trial',
        }

        unit_template_path = field_template_path(
            field='entry_unit', provider=self.plan.provider.billing_name
        )

        description_template_path = field_template_path(
            field='entry_description', provider=self.plan.provider.billing_name
        )

        # Add all the metered features consumed during the trial period
        for metered_feature in self.plan.metered_features.all():
            context.update({'metered-feature': metered_feature,
                            'name': metered_feature.name})

            unit = render_to_string(unit_template_path, context)

            qs = self.mf_log_entries.filter(metered_feature=metered_feature,
                                            start_date__gte=start_date,
                                            end_date__lte=end_date)
            log = [qs_item.consumed_units for qs_item in qs]
            total_consumed_units = reduce(lambda x, y: x + y, log, 0)

            extra_consumed_units = self._get_consumed_units_during_trial(
                metered_feature, total_consumed_units)

            if extra_consumed_units > 0:
                free_units = metered_feature.included_units_during_trial
                charged_units = extra_consumed_units
            else:
                free_units = total_consumed_units
                charged_units = 0

            if free_units > 0:
                description_template_path = field_template_path(
                    field='entry_description',
                    provider=self.plan.provider.billing_name
                )

                description = render_to_string(
                    description_template_path, context
                )

                # Positive value for the consumed items.
                DocumentEntry.objects.create(
                    invoice=invoice, proforma=proforma, description=description,
                    unit=unit, quantity=free_units,
                    unit_price=metered_feature.price_per_unit,
                    product_code=metered_feature.product_code,
                    start_date=start_date, end_date=end_date
                )

                context.update({
                    'context': 'mfs-trial-discount'
                })

                description = render_to_string(
                    description_template_path, context
                )

                # Negative value for the consumed items.
                DocumentEntry.objects.create(
                    invoice=invoice, proforma=proforma, description=description,
                    unit=unit, quantity=free_units,
                    unit_price=-metered_feature.price_per_unit,
                    product_code=metered_feature.product_code,
                    start_date=start_date, end_date=end_date
                )

            # Extra items consumed items that are not included
            if charged_units > 0:
                context.update({
                    'context': 'mfs-trial-not-discounted'
                })

                description = render_to_string(
                    description_template_path, context
                )

                DocumentEntry.objects.create(
                    invoice=invoice, proforma=proforma,
                    description=description, unit=unit,
                    quantity=charged_units,
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

        context = {
            'name': self.plan.name,
            'subscription': self,
            'plan': self.plan,
            'provider': self.plan.provider,
            'customer': self.customer,
            'product_code': self.plan.product_code,
            'start_date': start_date,
            'end_date': end_date,
            'prorated': prorated,
            'proration_percentage': percent,
            'context': 'plan'
        }

        description_template_path = field_template_path(
            field='entry_description', provider=self.plan.provider.billing_name
        )

        description = render_to_string(description_template_path, context)

        # Get the plan's prorated value
        plan_price = self.plan.amount * percent

        unit = '%ss' % self.plan.interval
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

        context = {
            'name': self.plan.name,
            'subscription': self,
            'plan': self.plan,
            'provider': self.plan.provider,
            'customer': self.customer,
            'product_code': self.plan.product_code,
            'start_date': start_date,
            'end_date': end_date,
            'prorated': prorated,
            'proration_percentage': percent,
            'context': 'mfs'
        }

        description_template_path = field_template_path(
            field='entry_description', provider=self.plan.provider.billing_name
        )

        for metered_feature in self.plan.metered_features.all():
            consumed_units = self._get_consumed_units(metered_feature,
                                                      percent, start_date,
                                                      end_date)
            if consumed_units > 0:
                description = render_to_string(
                    description_template_path, context)

                DocumentEntry.objects.create(
                    invoice=invoice, proforma=proforma,
                    description=description, unit=metered_feature.unit,
                    quantity=consumed_units, prorated=prorated,
                    unit_price=metered_feature.price_per_unit,
                    product_code=metered_feature.product_code,
                    start_date=start_date, end_date=end_date)

    def _get_proration_status_and_percent(self, start_date, end_date):
        """
        Returns the proration percent (how much of the interval will be billed)
        and the status (if the subscription is prorated or not).

        :param date: the date at which the percent and status are calculated
        :returns: a tuple containing (Decimal(percent), status) where status
            can be one of [True, False]. The decimal value will from the
            interval [0.00; 1.00].
        :rtype: tuple
        """

        intervals = {
            'year': {'years': -self.plan.interval_count},
            'month': {'months': -self.plan.interval_count},
            'week': {'weeks': -self.plan.interval_count},
            'day': {'days': -self.plan.interval_count},
        }

        # This will be UTC, which implies a max difference of 27 hours ~= 1 day
        # NOTE (Important): this will be a NEGATIVE INTERVAL (e.g.: -1 month,
        # -1 week, etc.)
        interval_len = relativedelta(**intervals[self.plan.interval])

        if end_date + interval_len >= start_date:
            # |start_date|---|start_date+interval_len|---|end_date|
            # => not prorated
            return False, Decimal('1.0000')
        else:
            # |start_date|---|end_date|---|start_date+interval_len|
            # => prorated
            interval_start = end_date + interval_len
            days_in_interval = (end_date - interval_start).days
            days_since_subscription_start = (end_date - start_date).days
            percent = 1.0 * days_since_subscription_start / days_in_interval
            percent = Decimal(percent).quantize(Decimal('0.0000'))

            return True, percent

    def __unicode__(self):
        return '%s (%s)' % (self.customer, self.plan)


class BillingLog(models.Model):
    subscription = models.ForeignKey('Subscription',
                                     related_name='billing_log_entries')
    invoice = models.ForeignKey('Invoice', null=True, blank=True,
                                related_name='billing_log_entries')
    proforma = models.ForeignKey('Proforma', null=True, blank=True,
                                 related_name='billing_log_entries')
    billing_date = models.DateField(
        help_text="The date when the invoice/proforma was issued."
    )

    class Meta:
        ordering = ['-billing_date']


class AbstractBillingEntity(LiveModel):
    name = models.CharField(
        max_length=128,
        help_text='The name to be used for billing purposes.'
    )
    company = models.CharField(max_length=128, blank=True, null=True)
    email = models.EmailField(max_length=254, blank=True, null=True)
    address_1 = models.CharField(max_length=128)
    address_2 = models.CharField(max_length=128, blank=True, null=True)
    country = models.CharField(choices=countries, max_length=3)
    city = models.CharField(max_length=128)
    state = models.CharField(max_length=128, blank=True, null=True)
    zip_code = models.CharField(max_length=32, blank=True, null=True)
    extra = models.TextField(
        blank=True, null=True,
        help_text='Extra information to display on the invoice '
                  '(markdown formatted).'
    )
    meta = jsonfield.JSONField(blank=True, null=True)

    class Meta:
        abstract = True

    @property
    def billing_name(self):
        return self.company or self.name

    @property
    def slug(self):
        return slugify(self.billing_name)

    def address(self):
        return ", ".join(filter(None, [self.address_1, self.city, self.state,
                                       self.zip_code, self.country]))
    address.short_description = 'Address'

    def __unicode__(self):
        return self.billing_name

    def get_list_display_fields(self):
        field_names = ['company', 'email', 'address_1', 'city', 'country',
                       'zip_code']
        return [getattr(self, field, '') for field in field_names]

    def get_archivable_field_values(self):
        field_names = ['name', 'company', 'email', 'address_1', 'address_2',
                       'city', 'country', 'city', 'state', 'zip_code', 'extra',
                       'meta']
        return {field: getattr(self, field, '') for field in field_names}


class Customer(AbstractBillingEntity):
    payment_due_days = models.PositiveIntegerField(
        default=PAYMENT_DUE_DAYS,
        help_text='Due days for generated proforma/invoice.'
    )
    consolidated_billing = models.BooleanField(
        default=False, help_text='A flag indicating consolidated billing.'
    )
    customer_reference = models.CharField(
        max_length=256, blank=True, null=True,
        help_text="It's a reference to be passed between silver and clients. "
                  "It usually points to an account ID."
    )
    sales_tax_number = models.CharField(max_length=64, blank=True, null=True)
    sales_tax_percent = models.DecimalField(
        max_digits=4, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0.0)],
        help_text="Whenever to add sales tax. "
                  "If null, it won't show up on the invoice."
    )
    sales_tax_name = models.CharField(
        max_length=64, null=True, blank=True,
        help_text="Sales tax name (eg. 'sales tax' or 'VAT')."
    )

    def __init__(self, *args, **kwargs):
        super(Customer, self).__init__(*args, **kwargs)
        company_field = self._meta.get_field_by_name("company")[0]
        company_field.help_text = "The company to which the bill is issued."

    def clean(self):
        if (self.sales_tax_number and
            is_vat_number_format_valid(self.sales_tax_number,
                                       self.country) is False):
            raise ValidationError(
                {'sales_tax_number': 'The sales tax number is not valid.'}
            )

    def delete(self):
        subscriptions = Subscription.objects.filter(customer=self)
        for sub in subscriptions:
            try:
                sub.cancel()
                sub.save()
            except TransitionNotAllowed:
                pass
        super(Customer, self).delete()

    def __unicode__(self):
        return " - ".join(filter(None, [self.name, self.company]))

    def get_archivable_field_values(self):
        base_fields = super(Customer, self).get_archivable_field_values()
        customer_fields = ['customer_reference', 'consolidated_billing',
                           'payment_due_days', 'sales_tax_number',
                           'sales_tax_percent']
        fields_dict = {field: getattr(self, field, '') for field in
                       customer_fields}
        base_fields.update(fields_dict)
        return base_fields


class Provider(AbstractBillingEntity):
    FLOW_CHOICES = (
        ('proforma', 'Proforma'),
        ('invoice', 'Invoice'),
    )
    DOCUMENT_DEFAULT_STATE = (
        ('draft', 'Draft'),
        ('issued', 'Issued')
    )

    flow = models.CharField(
        max_length=10, choices=FLOW_CHOICES,
        default=FLOW_CHOICES[0][0],
        help_text="One of the available workflows for generating proformas and\
                   invoices (see the documentation for more details)."
    )
    invoice_series = models.CharField(
        max_length=20,
        help_text="The series that will be used on every invoice generated by\
                   this provider."
    )
    invoice_starting_number = models.PositiveIntegerField()
    proforma_series = models.CharField(
        max_length=20, blank=True, null=True,
        help_text="The series that will be used on every proforma generated by\
                   this provider."
    )
    proforma_starting_number = models.PositiveIntegerField(
        blank=True, null=True
    )
    default_document_state = models.CharField(
        max_length=10, choices=DOCUMENT_DEFAULT_STATE,
        default=DOCUMENT_DEFAULT_STATE[0][0],
        help_text="The default state of the auto-generated documents."
    )

    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        company_field = self._meta.get_field_by_name("company")[0]
        company_field.help_text = "The provider issuing the invoice."

    def clean(self):
        if self.flow == 'proforma':
            if not self.proforma_starting_number and\
               not self.proforma_series:
                errors = {'proforma_series': "This field is required as the "
                                             "chosen flow is proforma.",
                          'proforma_starting_number': "This field is required "
                                                      "as the chosen flow is "
                                                      "proforma."}
                raise ValidationError(errors)
            elif not self.proforma_series:
                errors = {'proforma_series': "This field is required as the "
                                             "chosen flow is proforma."}
                raise ValidationError(errors)
            elif not self.proforma_starting_number:
                errors = {'proforma_starting_number': "This field is required "
                                                      "as the chosen flow is "
                                                      "proforma."}
                raise ValidationError(errors)

    def get_invoice_archivable_field_values(self):
        base_fields = super(Provider, self).get_archivable_field_values()
        base_fields.update({'invoice_series': getattr(self, 'invoice_series', '')})
        return base_fields

    def get_proforma_archivable_field_values(self):
        base_fields = super(Provider, self).get_archivable_field_values()
        base_fields.update({'proforma_series': getattr(self, 'proforma_series', '')})
        return base_fields

    @property
    def model_corresponding_to_default_flow(self):
        return Proforma if self.flow == 'proforma' else Invoice

    def __unicode__(self):
        return " - ".join(filter(None, [self.name, self.company]))


@receiver(pre_save, sender=Provider)
def update_draft_billing_documents(sender, instance, **kwargs):
    if instance.pk:
        provider = Provider.objects.get(pk=instance.pk)
        old_invoice_series = provider.invoice_series
        old_proforma_series = provider.proforma_series

        if instance.invoice_series != old_invoice_series:
            for invoice in Invoice.objects.filter(state='draft',
                                                  provider=provider):
                # update the series for draft invoices
                invoice.series = instance.invoice_series
                # the number will be automatically updated in the save method
                invoice.number = None
                invoice.save()

        if instance.proforma_series != old_proforma_series:
            for proforma in Proforma.objects.filter(state='draft',
                                                    provider=provider):
                # update the series for draft invoices
                proforma.series = instance.proforma_series
                # the number will be automatically updated in the save method
                proforma.number = None
                proforma.save()


class ProductCode(models.Model):
    value = models.CharField(max_length=128, unique=True)

    def __unicode__(self):
        return self.value


class BillingDocument(models.Model):
    states = ['draft', 'issued', 'paid', 'canceled']
    STATE_CHOICES = tuple((state, state.replace('_', ' ').title())
                          for state in states)
    series = models.CharField(max_length=20, blank=True, null=True)
    number = models.IntegerField(blank=True, null=True)
    customer = models.ForeignKey('Customer')
    provider = models.ForeignKey('Provider')
    archived_customer = jsonfield.JSONField()
    archived_provider = jsonfield.JSONField()
    due_date = models.DateField(null=True, blank=True)
    issue_date = models.DateField(null=True, blank=True)
    paid_date = models.DateField(null=True, blank=True)
    cancel_date = models.DateField(null=True, blank=True)
    sales_tax_percent = models.DecimalField(max_digits=4, decimal_places=2,
                                            validators=[MinValueValidator(0.0)],
                                            null=True, blank=True)
    sales_tax_name = models.CharField(max_length=64, blank=True, null=True)
    currency = models.CharField(
        choices=currencies, max_length=4, default='USD',
        help_text='The currency used for billing.')
    pdf = models.FileField(null=True, blank=True, editable=False,
                           storage=_storage, upload_to=documents_pdf_path)
    state = FSMField(choices=STATE_CHOICES, max_length=10, default=states[0],
        verbose_name="State", help_text='The state the invoice is in.')

    __last_state = None

    class Meta:
        abstract = True
        unique_together = ('provider', 'series', 'number')
        ordering = ('-issue_date', 'series', 'number')

    def __init__(self, *args, **kwargs):
        super(BillingDocument, self).__init__(*args, **kwargs)
        self.__last_state = self.state

    @transition(field=state, source='draft', target='issued')
    def issue(self, issue_date=None, due_date=None):
        if issue_date:
            self.issue_date = dt.strptime(issue_date, '%Y-%m-%d').date()
        elif not self.issue_date and not issue_date:
            self.issue_date = timezone.now().date()

        if due_date:
            self.due_date = dt.strptime(due_date, '%Y-%m-%d').date()
        elif not self.due_date and not due_date:
            delta = datetime.timedelta(days=PAYMENT_DUE_DAYS)
            self.due_date = timezone.now().date() + delta

        if not self.sales_tax_name:
            self.sales_tax_name = self.customer.sales_tax_name
        if not self.sales_tax_percent:
            self.sales_tax_percent = self.customer.sales_tax_percent

        self.archived_customer = self.customer.get_archivable_field_values()

        self._save_pdf(state='issued')

    @transition(field=state, source='issued', target='paid')
    def pay(self, paid_date=None):
        if paid_date:
            self.paid_date = dt.strptime(paid_date, '%Y-%m-%d').date()
        if not self.paid_date and not paid_date:
            self.paid_date = timezone.now().date()

        self._save_pdf(state='paid')

    @transition(field=state, source='issued', target='canceled')
    def cancel(self, cancel_date=None):
        if cancel_date:
            self.cancel_date = dt.strptime(cancel_date, '%Y-%m-%d').date()
        if not self.cancel_date and not cancel_date:
            self.cancel_date = timezone.now().date()

        self._save_pdf(state='canceled')

    def clean(self):
        super(BillingDocument, self).clean()

        # The only change that is allowed if the document is in issued state
        # is the state chage from issued to paid
        # !! TODO: If __last_state == 'issued' and self.state == 'paid' || 'canceled'
        # it should also be checked that the other fields are the same bc.
        # right now a document can be in issued state and someone could
        # send a request which contains the state = 'paid' and also send
        # other changed fields and the request would be accepted bc. only
        # the state is verified.
        if self.__last_state == 'issued' and self.state not in ['paid', 'canceled']:
            msg = 'You cannot edit the document once it is in issued state.'
            raise ValidationError({NON_FIELD_ERRORS: msg})

        if self.__last_state == 'canceled':
            msg = 'You cannot edit the document once it is in canceled state.'
            raise ValidationError({NON_FIELD_ERRORS: msg})

        # If it's in paid state => don't allow any changes
        if self.__last_state == 'paid':
            msg = 'You cannot edit the document once it is in paid state.'
            raise ValidationError({NON_FIELD_ERRORS: msg})

    def save(self, *args, **kwargs):
        if not self.series:
            self.series = self.default_series

        # Generate the number
        if not self.number:
            self.number = self._generate_number()

        # Add tax info
        if not self.sales_tax_name:
            self.sales_tax_name = self.customer.sales_tax_name
        if not self.sales_tax_percent:
            self.sales_tax_percent = self.customer.sales_tax_percent

        self.__last_state = self.state
        super(BillingDocument, self).save(*args, **kwargs)

    def _generate_number(self):
        """Generates the number for a proforma/invoice."""
        documents = self.__class__._default_manager.filter(
            provider=self.provider, series=self.series
        )
        if not documents.exists():
            # An invoice/proforma with this provider and series does not exist
            if self.series == self.default_series:
                return self._starting_number
            else:
                return 1
        else:
            # An invoice with this provider and series already exists
            max_existing_number = documents.aggregate(
                Max('number')
            )['number__max']
            if max_existing_number:
                if self._starting_number:
                    return max(max_existing_number + 1, self._starting_number)
                else:
                    return max_existing_number + 1
            else:
                return 1

    def __unicode__(self):
        return '%s-%s %s => %s [%.2f %s]' % (self.series, self.number,
                                             self.provider.billing_name,
                                             self.customer.billing_name,
                                             self.total, self.currency)

    def _entity_display(self, entity):
        display = '%s (%s, %s)' % (entity.billing_name, entity.name,
                                   entity.email)
        return display

    def customer_display(self):
        try:
            return self._entity_display(self.customer)
        except Customer.DoesNotExist:
            return ''
    customer_display.short_description = 'Customer'
    customer_display.admin_order_field = 'customer'

    def provider_display(self):
        try:
            return self._entity_display(self.provider)
        except Customer.DoesNotExist:
            return ''
    provider_display.short_description = 'Provider'
    provider_display.admin_order_field = 'provider'

    @property
    def updateable_fields(self):
        return ['customer', 'provider', 'due_date', 'issue_date', 'paid_date',
                'cancel_date', 'sales_tax_percent', 'sales_tax_name',
                'currency']

    @property
    def _entries(self):
        # entries iterator which replaces the invoice/proforma from the DB with
        # self. We need this in _generate_pdf so that the data in PDF has the
        # lastest state for the document. Without this we get in template:
        #
        # invoice.issue_date != entry.invoice.issue_date
        #
        # which is obviously false.
        document_type_name = self.__class__.__name__  # Invoice or Proforma
        kwargs = {document_type_name.lower(): self}
        entries = DocumentEntry.objects.filter(**kwargs)
        for entry in entries:
            if document_type_name.lower() == 'invoice':
                entry.invoice = self
            if document_type_name.lower() == 'proforma':
                entry.proforma = self
            yield(entry)

    def _generate_pdf(self, state=None):
        customer = Customer(**self.archived_customer)
        provider = Provider(**self.archived_provider)
        if state is None:
            state = self.state

        context = {
            'document': self,
            'provider': provider,
            'customer': customer,
            'entries': self._entries,
            'state': state
        }

        provider_state_template = '{provider}/{kind}_{state}_pdf.html'.format(
            kind=self.kind, provider=self.provider.slug, state=state).lower()
        provider_template = '{provider}/{kind}_pdf.html'.format(
            kind=self.kind, provider=self.provider.slug).lower()
        generic_state_template = '{kind}_{state}_pdf.html'.format(
            kind=self.kind, state=state).lower()
        generic_template = '{kind}_pdf.html'.format(
            kind=self.kind).lower()
        _templates = [provider_state_template, provider_template,
                      generic_state_template, generic_template]

        templates = []
        for t in _templates:
            templates.append('billing_documents/' + t)

        template = select_template(templates)

        file_object = HttpResponse(content_type='application/pdf')
        generate_pdf_template_object(template, file_object, context)

        return file_object

    def _save_pdf(self, state=None):
        file_object = self._generate_pdf(state)

        if file_object:
            pdf_content = ContentFile(file_object)
            filename = '{doc_type}_{series}-{number}.pdf'.format(
                doc_type=self.__class__.__name__,
                series=self.series,
                number=self.number
            )

            if self.pdf:
                self.pdf.delete()
            self.pdf.save(filename, pdf_content, False)
        else:
            raise RuntimeError(_('Could not generate invoice pdf.'))

    def serialize_hook(self, hook):
        """
        Used to generate a skinny payload.
        """

        return {
            'hook': hook.dict(),
            'data': {
                'id': self.id
            }
        }


class Invoice(BillingDocument):
    proforma = models.ForeignKey('Proforma', blank=True, null=True,
                                 related_name='related_proforma')

    kind = 'Invoice'

    def __init__(self, *args, **kwargs):
        super(Invoice, self).__init__(*args, **kwargs)

        provider_field = self._meta.get_field_by_name("provider")[0]
        provider_field.related_name = "invoices"

        customer_field = self._meta.get_field_by_name("customer")[0]
        customer_field.related_name = "invoices"

    @transition(field='state', source='draft', target='issued')
    def issue(self, issue_date=None, due_date=None):
        self.archived_provider = self.provider.get_invoice_archivable_field_values()

        super(Invoice, self).issue(issue_date, due_date)

    @property
    def _starting_number(self):
        return self.provider.invoice_starting_number

    @property
    def default_series(self):
        try:
            return self.provider.invoice_series
        except Provider.DoesNotExist:
            return ''

    @property
    def total(self):
        entries_total = [Decimal(item.total)
                         for item in self.invoice_entries.all()]
        res = reduce(lambda x, y: x + y, entries_total, Decimal('0.00'))
        return res

    @property
    def total_before_tax(self):
        entries_total = [Decimal(item.total_before_tax)
                         for item in self.invoice_entries.all()]
        res = reduce(lambda x, y: x + y, entries_total, Decimal('0.0000'))
        return res

    @property
    def tax_value(self):
        entries_total = [Decimal(item.tax_value)
                         for item in self.invoice_entries.all()]
        res = reduce(lambda x, y: x + y, entries_total, Decimal('0.0000'))
        return res


@receiver(pre_delete, sender=Invoice)
def delete_invoice_pdf_from_storage(sender, instance, **kwargs):
    if instance.pdf:
        # Delete the invoice's PDF
        instance.pdf.delete(False)

    # If exists, delete the PDF of the related proforma
    if instance.proforma:
        if instance.proforma.pdf:
            instance.proforma.pdf.delete(False)


class Proforma(BillingDocument):
    invoice = models.ForeignKey('Invoice', blank=True, null=True,
                                related_name='related_invoice')

    kind = 'Proforma'

    def __init__(self, *args, **kwargs):
        super(Proforma, self).__init__(*args, **kwargs)

        provider_field = self._meta.get_field_by_name("provider")[0]
        provider_field.related_name = "proformas"

        customer_field = self._meta.get_field_by_name("customer")[0]
        customer_field.related_name = "proformas"

    def clean(self):
        super(Proforma, self).clean()
        if not self.series:
            if not hasattr(self, 'provider'):
                # the clean method is called even if the clean_fields method
                # raises exceptions, so we check if the provider was specified
                pass
            elif self.provider.proforma_series:
                err_msg = {'series': 'You must either specify the series or '
                                     'set a default proforma_series for the '
                                     'provider.'}
                raise ValidationError(err_msg)

    @transition(field='state', source='draft', target='issued')
    def issue(self, issue_date=None, due_date=None):
        self.archived_provider = self.provider.get_proforma_archivable_field_values()

        super(Proforma, self).issue(issue_date, due_date)

    @transition(field='state', source='issued', target='paid')
    def pay(self, paid_date=None):
        super(Proforma, self).pay(paid_date)

        if not self.invoice:
            self.invoice = self._new_invoice()
            self.invoice.issue()
            self.invoice.pay()
            self.save()
        else:
            self.invoice.pay()
            self.invoice.save()

    def create_invoice(self):
        if self.state != "issued":
            raise ValueError("You can't create an invoice from a %s proforma, "
                             "only from an issued one" % self.state)

        if self.invoice:
            raise ValueError("This proforma already has an invoice { %s }"
                             % self.invoice)

        self.invoice = self._new_invoice()
        self.invoice.issue()
        self.invoice.save()

        self.save()

    def _new_invoice(self):
        # Generate the new invoice based this proforma
        invoice_fields = self.fields_for_automatic_invoice_generation
        invoice_fields.update({'proforma': self})
        invoice = Invoice.objects.create(**invoice_fields)

        # For all the entries in the proforma => add the link to the new
        # invoice
        DocumentEntry.objects.filter(proforma=self).update(invoice=invoice)
        return invoice

    @property
    def _starting_number(self):
        return self.provider.proforma_starting_number

    @property
    def default_series(self):
        try:
            return self.provider.proforma_series
        except Provider.DoesNotExist:
            return ''

    @property
    def fields_for_automatic_invoice_generation(self):
        fields = ['customer', 'provider', 'archived_customer',
                  'archived_provider', 'paid_date', 'cancel_date',
                  'sales_tax_percent', 'sales_tax_name', 'currency']
        return {field: getattr(self, field, None) for field in fields}

    @property
    def total(self):
        entries_total = [Decimal(item.total)
                         for item in self.proforma_entries.all()]
        res = reduce(lambda x, y: x + y, entries_total, Decimal('0.0000'))
        return res

    @property
    def total_before_tax(self):
        entries_total = [Decimal(item.total_before_tax)
                         for item in self.proforma_entries.all()]
        res = reduce(lambda x, y: x + y, entries_total, Decimal('0.0000'))
        return res

    @property
    def tax_value(self):
        entries_total = [Decimal(item.tax_value)
                         for item in self.proforma_entries.all()]
        res = reduce(lambda x, y: x + y, entries_total, Decimal('0.0000'))
        return res


@receiver(pre_delete, sender=Proforma)
def delete_proforma_pdf_from_storage(sender, instance, **kwargs):
    if instance.pdf:
        # Delete the proforma's PDF
        instance.pdf.delete(False)

    # If exists, delete the PDF of the related invoice
    if instance.invoice:
        if instance.invoice.pdf:
            instance.invoice.pdf.delete(False)


class DocumentEntry(models.Model):
    description = models.CharField(max_length=1024)
    unit = models.CharField(max_length=1024, blank=True, null=True)
    quantity = models.DecimalField(max_digits=19, decimal_places=2,
                                   validators=[MinValueValidator(0.0)])
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    product_code = models.ForeignKey('ProductCode', null=True, blank=True,
                                     related_name='invoices')
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    prorated = models.BooleanField(default=False)
    invoice = models.ForeignKey('Invoice', related_name='invoice_entries',
                                blank=True, null=True)
    proforma = models.ForeignKey('Proforma', related_name='proforma_entries',
                                 blank=True, null=True)

    class Meta:
        verbose_name = 'Entry'
        verbose_name_plural = 'Entries'

    @property
    def total(self):
        res = self.total_before_tax + self.tax_value
        return res.quantize(Decimal('0.0000'))

    @property
    def total_before_tax(self):
        res = Decimal(self.quantity * self.unit_price)
        return res.quantize(Decimal('0.0000'))

    @property
    def tax_value(self):
        if self.invoice:
            sales_tax_percent = self.invoice.sales_tax_percent
        elif self.proforma:
            sales_tax_percent = self.proforma.sales_tax_percent
        else:
            sales_tax_percent = None

        if not sales_tax_percent:
            return Decimal(0)

        res = Decimal(self.total_before_tax * sales_tax_percent / 100)
        return res.quantize(Decimal('0.0000'))

    def __unicode__(self):
        s = "{descr} - {unit} - {unit_price} - {quantity} - {product_code}"
        return s.format(
            descr=self.description,
            unit=self.unit,
            unit_price=self.unit_price,
            quantity=self.quantity,
            product_code=self.product_code)
