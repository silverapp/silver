"""Models for the silver app."""
import datetime
from datetime import datetime as dt
from decimal import Decimal

import jsonfield
from django_fsm import FSMField, transition, TransitionNotAllowed
from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
from django.core.files.base import ContentFile
from django.http import HttpResponse
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.utils.module_loading import import_string
from django.utils.text import slugify
from django_xhtml2pdf.utils import generate_pdf
from django.db import models
from django.db.models import Max
from django.conf import settings
from django.db.models.signals import pre_delete
from django.dispatch.dispatcher import receiver
from international.models import countries, currencies
from livefield.models import LiveModel
from dateutil.relativedelta import *
from dateutil.rrule import *
from pyvat import is_vat_number_format_valid

from silver.api.dateutils import (last_date_that_fits, next_date_after_period,
                                  next_date_after_date)
from silver.utils import get_object_or_None


UPDATE_TYPES = (
    ('absolute', 'Absolute'),
    ('relative', 'Relative')
)

PAYMENT_DUE_DAYS = getattr(settings, 'SILVER_DEFAULT_DUE_DAYS', 5)

_storage = getattr(settings, 'SILVER_DOCUMENT_STORAGE', None)
if _storage:
    _storage_klass = import_string(_storage[0])
    _storage = _storage_klass(*_storage[1], **_storage[2])


def documents_pdf_path(document, filename):
    path = '{prefix}{company}/{doc_name}/{date}/{filename}'.format(
        company=slugify(document.provider.company or document.provider.name),
        date=document.issue_date.strftime('%Y/%m'),
        doc_name=('%ss' % document.__class__.__name__).lower(),
        prefix=getattr(settings, 'SILVER_DOCUMENT_PREFIX', ''),
        filename=filename)
    return path


class Plan(models.Model):
    INTERVALS = (
        ('day', 'Day'),
        ('week', 'Week'),
        ('month', 'Month'),
        ('year', 'Year')
    )

    name = models.CharField(
        max_length=20, help_text='Display name of the plan.'
    )
    interval = models.CharField(
        choices=INTERVALS, max_length=12, default=INTERVALS[2][0],
        help_text='The frequency with which a subscription should be billed.'
    )
    interval_count = models.PositiveIntegerField(
        help_text='The number of intervals between each subscription billing'
    )
    amount = models.DecimalField(
        max_digits=8, decimal_places=2,
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
        'MeteredFeature', blank=True, null=True,
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
        'ProductCode', unique=True, help_text='The product code for this plan.'
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
        max_length=32,
        help_text='The feature display name.'
    )
    unit = models.CharField(max_length=20)
    price_per_unit = models.DecimalField(
        max_digits=8, decimal_places=2, help_text='The price per unit.'
    )
    included_units = models.DecimalField(
        max_digits=8, decimal_places=2,
        help_text='The number of included units per plan interval.'
    )
    product_code = models.ForeignKey(
        'ProductCode', help_text='The product code for this plan.'
    )

    def __unicode__(self):
        return self.name


class MeteredFeatureUnitsLog(models.Model):
    metered_feature = models.ForeignKey('MeteredFeature', related_name='consumed')
    subscription = models.ForeignKey('Subscription', related_name='mf_log_entries')
    consumed_units = models.DecimalField(max_digits=8, decimal_places=2)
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

    def clean(self):
        if self.start_date and self.trial_end:
            if self.trial_end < self.start_date:
                raise ValidationError(
                    {'trial_end': 'The trial end date cannot be older than '
                                  'the subscription start date.'}
                )

    def _current_start_date(self, reference_date=None, ignore_trial=None):
        ignore_trial_default = False
        ignore_trial = ignore_trial_default or ignore_trial

        if reference_date is None:
            reference_date = timezone.now().date()

        # if the trial_end date is ignored, it doesn't exist
        # or it hasn't passed yet: we don't consider it
        if (ignore_trial or not self.trial_end) \
                or self.trial_end >= reference_date:
            # now we act depending on the interval type
            if self.plan.interval == 'month':
                # the fake_initial_date is used to normalize the starting dates
                # of intervals, by fixing a day
                fake_initial_date = next_date_after_date(
                    initial_date=self.start_date, day=1
                )
                # this returns the appropriate start date
                return last_date_that_fits(
                    initial_date=fake_initial_date,
                    interval_type=self.plan.interval,
                    interval_count=self.plan.interval_count,
                    end_date=reference_date
                ) or self.start_date
            else:
                fake_initial_date = last_date_that_fits(
                    initial_date=self.start_date,
                    interval_type=self.plan.interval,
                    interval_count=self.plan.interval_count,
                    end_date=reference_date
                )
                return fake_initial_date
        # if the trial_end has passed
        else:
            # now we act depending on the interval type
            if self.plan.interval == 'month':
                # we get a fake_initial_date based on the trial_end date
                # and on a fixed day
                fake_initial_date = next_date_after_date(
                    initial_date=self.trial_end, day=1
                )
            else:
                fake_initial_date = last_date_that_fits(
                    initial_date=self.trial_end,
                    interval_type=self.plan.interval,
                    interval_count=self.plan.interval_count,
                    end_date=reference_date
                ) + datetime.timedelta(days=1)
            if fake_initial_date:
                # if the fake_initial_date has not arrived or passed yet
                if reference_date < fake_initial_date:
                    # it means the start_date is the next day after trial_end
                    fake_initial_date = (self.trial_end +
                                         datetime.timedelta(days=1))

            # based on the fake_initial_date we return an appropriate start date
            return last_date_that_fits(
                initial_date=fake_initial_date,
                end_date=reference_date,
                interval_type=self.plan.interval,
                interval_count=self.plan.interval_count
            )

    def _current_end_date(self, reference_date=None, ignore_trial=None):
        ignore_trial_default = False
        ignore_trial = ignore_trial_default or ignore_trial

        if reference_date is None:
            reference_date = timezone.now().date()

        end_date = None
        _current_start_date = self._current_start_date(reference_date,
                                                       ignore_trial)
        if not _current_start_date:
            return None

        if self.plan.interval == 'month':
            fake_end_date = next_date_after_date(
                initial_date=_current_start_date,
                day=1
            ) - datetime.timedelta(days=1)
        else:
            fake_end_date = next_date_after_period(
                initial_date=_current_start_date,
                interval_type=self.plan.interval,
                interval_count=self.plan.interval_count
            ) - datetime.timedelta(days=1)

        if (ignore_trial or not self.trial_end) \
                or self.trial_end >= reference_date:
            if self.trial_end and fake_end_date \
                    and fake_end_date > self.trial_end:
                end_date = self.trial_end
            else:
                end_date = fake_end_date
        else:
            if fake_end_date:
                if reference_date < fake_end_date:
                    end_date = fake_end_date

            end_date = end_date or (next_date_after_period(
                initial_date=_current_start_date,
                interval_type=self.plan.interval,
                interval_count=self.plan.interval_count
            ) - datetime.timedelta(days=1))

        if end_date:
            if self.ended_at:
                if self.ended_at < end_date:
                    end_date = self.ended_at
            return end_date
        return None

    @property
    def current_start_date(self):
        return self._current_start_date(ignore_trial=True)

    @property
    def current_end_date(self):
        return self._current_end_date(ignore_trial=True)

    def bucket_start_date(self, reference_date=None):
        return self._current_start_date(reference_date=reference_date,
                                        ignore_trial=False)

    def bucket_end_date(self, reference_date=None):
        return self._current_end_date(reference_date=reference_date,
                                      ignore_trial=False)

    def is_on_trial(self):
        return timezone.now().date() <= self.trial_end and self.state != 'canceled'

    def _should_reissue(self, last_billing_date):
        last_billing_date = datetime.datetime(
            year=last_billing_date.year,
            month=last_billing_date.month,
            day=last_billing_date.day,
            tzinfo=timezone.get_current_timezone()
        )
        intervals = {
            'year': {'years': +self.plan.interval_count},
            'month': {'months': +self.plan.interval_count},
            'week': {'weeks': +self.plan.interval_count},
            'day': {'days': +self.plan.interval_count}
        }

        # generate one object of 'year', 'month', 'week, ...
        interval_length = relativedelta(**intervals[self.plan.interval])
        generate_after = datetime.timedelta(seconds=self.plan.generate_after)
        interval_end = last_billing_date + interval_length + generate_after

        return timezone.now() > interval_end

    def _should_issue_first_time(self):
        # Get the datetime object for the next interval
        # yearly plans - first day of next year + generate_after
        # monthly plans - first day of next month + generate_after
        # weekly plans - next monday + generate_after
        # daily plans - next day (start_date + 1) + generate_after
        if self.plan.interval == 'year':
            count = 2 if self.start_date.month == self.start_date.day == 1 else 1
            next_interval_start = list(rrule(YEARLY,
                                             interval=self.plan.interval_count,
                                             byyearday=1,
                                             count=count,
                                             dtstart=self.start_date))[-1]
        elif self.plan.interval == 'month':
            count = 2 if self.start_date.month == self.start_date.day == 1 else 1
            next_interval_start = list(rrule(MONTHLY,
                                             interval=self.plan.interval_count,
                                             count=count,
                                             bymonthday=1,
                                             dtstart=self.start_date))[-1]
        elif self.plan.interval == 'week':
            count = 2 if self.start_date.month == self.start_date.day == 1 else 1
            next_interval_start = list(rrule(WEEKLY,
                                             interval=self.plan.interval_count,
                                             count=count,
                                             byweekday=MO,
                                             dtstart=self.start_date))[-1]
        elif self.plan.interval == 'day':
            days = self.plan.interval_count
            next_interval_start = self.start_date + datetime.timedelta(days=days)
            next_interval_start = dt(year=next_interval_start.year,
                                     month=next_interval_start.month,
                                     day=next_interval_start.day)

        current_timezone = timezone.get_current_timezone()
        next_interval_start = current_timezone.localize(next_interval_start)
        generate_after = datetime.timedelta(seconds=self.plan.generate_after)

        return timezone.now() > next_interval_start + generate_after

    @property
    def should_be_billed(self):
        if self.state == 'canceled':
            return True

        if self.is_billed_first_time:
            return self._should_issue_first_time()
        return self._should_reissue(self.last_billing_date)

    @property
    def is_billed_first_time(self):
        qs_count = self.billing_log_entries.all().count()
        return False if qs_count else True

    @property
    def last_billing_date(self):
        try:
            return self.billing_log_entries.all()[:1].get().last_billing_date
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
                    days=self.plan.trial_period_days - 1
                )

    @transition(field=state, source=['active'], target='canceled')
    def cancel(self):
        # XXX: shouldn't the trial_end date be set to now()?
        pass

    @transition(field=state, source='canceled', target='ended')
    def end(self):
        self.ended_at = timezone.now().date()

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

    class Meta:
        abstract = True

    @property
    def billing_name(self):
        return self.company or self.name

    @property
    def slug(self):
        return slugify(self.billing_name)

    def __unicode__(self):
        return self.billing_name

    def get_list_display_fields(self):
        field_names = ['company', 'email', 'address_1', 'city', 'country',
                       'zip_code']
        return [getattr(self, field, '') for field in field_names]

    def get_archivable_field_values(self):
        field_names = ['name', 'company', 'email', 'address_1', 'address_1',
                       'city', 'country', 'city', 'zip_code', 'zip_code',
                       'extra']
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
                          'payment_due_days']
        fields_dict = {field: getattr(self, field, '') for field in customer_fields}
        base_fields.update(fields_dict)
        return base_fields

    def complete_address(self):
        return ", ".join(filter(None, [self.address_1, self.city, self.state,
                                       self.zip_code, self.country]))
    complete_address.short_description = 'Complete address'


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

    def __unicode__(self):
        return " - ".join(filter(None, [self.name, self.company]))


class ProductCode(models.Model):
    value = models.CharField(max_length=128, unique=True)

    def __unicode__(self):
        return self.value


class BillingDocument(models.Model):
    states = ['draft', 'issued', 'paid', 'canceled']
    STATE_CHOICES = tuple((state, state.replace('_', ' ').title())
                          for state in states)

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
        unique_together = ('provider', 'number')
        ordering = ('-issue_date', 'number')

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

        self._generate_pdf()

    @transition(field=state, source='issued', target='paid')
    def pay(self, paid_date=None):
        if paid_date:
            self.paid_date = dt.strptime(paid_date, '%Y-%m-%d').date()
        if not self.paid_date and not paid_date:
            self.paid_date = timezone.now().date()

    @transition(field=state, source='issued', target='canceled')
    def cancel(self, cancel_date=None):
        if cancel_date:
            self.cancel_date = dt.strptime(cancel_date, '%Y-%m-%d').date()
        if not self.cancel_date and not cancel_date:
            self.cancel_date = timezone.now().date()

    def clean(self):
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
        """Generates the number for a proforma/invoice. To be implemented
        in the corresponding subclass."""

        if not self.__class__._default_manager.filter(
            provider=self.provider,
        ).exists():
            # An invoice with this provider does not exist
            return self.provider.invoice_starting_number
        else:
            # An invoice with this provider already exists
            max_existing_number = self.__class__._default_manager.filter(
                provider=self.provider,
            ).aggregate(Max('number'))['number__max']

            return max_existing_number + 1

    def __unicode__(self):
        return '%s-%s-%s' % (self.number, self.customer, self.provider)

    def customer_display(self):
        try:
            return ', '.join(self.customer.get_list_display_fields())
        except Customer.DoesNotExist:
            return ''
    customer_display.short_description = 'Customer'

    def provider_display(self):
        try:
            return ', '.join(self.provider.get_list_display_fields())
        except Customer.DoesNotExist:
            return ''
    provider_display.short_description = 'Provider'

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

    def _generate_pdf(self):

        customer = Customer(**self.archived_customer)
        provider = Provider(**self.archived_provider)

        context = {
            'invoice': self,
            'provider': provider,
            'customer': customer,
            'entries': self._entries
        }
        resp = HttpResponse(content_type='application/pdf')
        data = generate_pdf('silver/invoice_pdf.html', context=context,
                            file_object=resp)

        if data:
            pdf_content = ContentFile(data)
            filename = '{doc_type}_{series}-{number}.pdf'.format(
                doc_type=self.__class__.__name__,
                series=self.series,
                number=self.number
            )
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
    def series(self):
        try:
            return self.provider.invoice_series
        except Provider.DoesNotExist:
            return ''

    @property
    def total(self):
        entries_total = [Decimal(item.total) for item in self.invoice_entries.all()]
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
        # Delete the invoice's pdf
        instance.pdf.delete(False)

    # If exists, delete the pdf of the related proforma
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

    @transition(field='state', source='draft', target='issued')
    def issue(self, issue_date=None, due_date=None):
        self.archived_provider = self.provider.get_proforma_archivable_field_values()

        super(Proforma, self).issue(issue_date, due_date)

    @transition(field='state', source='issued', target='paid')
    def pay(self, paid_date=None):
        super(Proforma, self).pay(paid_date)

        # Generate the new invoice based this proforma
        invoice_fields = self.fields_for_automatic_invoice_generation
        invoice_fields.update({'proforma': self})
        invoice = Invoice.objects.create(**invoice_fields)
        # For all the entries in the proforma => add the link to the new
        # invoice
        DocumentEntry.objects.filter(proforma=self).update(invoice=invoice)
        invoice.issue()
        invoice.pay()
        invoice.save()

        self.invoice = invoice


    @property
    def series(self):
        try:
            return self.provider.proforma_series
        except Provider.DoesNotExist:
            return ''

    @property
    def fields_for_automatic_invoice_generation(self):
        fields = ['customer', 'provider', 'archived_customer',
                  'archived_provider', 'due_date', 'issue_date', 'paid_date',
                  'cancel_date', 'sales_tax_percent', 'sales_tax_name',
                  'currency']
        return {field: getattr(self, field, None) for field in fields}

    @property
    def total(self):
        entries_total = [Decimal(item.total) for item in self.proforma_entries.all()]
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
        # Delete the proforma's pdf
        instance.pdf.delete(False)

    # If exists, delete the pdf of the related invoice
    if instance.invoice:
        if instance.invoice.pdf:
            instance.invoice.pdf.delete(False)


class DocumentEntry(models.Model):
    description = models.CharField(max_length=255)
    unit = models.CharField(max_length=20, blank=True, null=True)
    quantity = models.DecimalField(max_digits=8, decimal_places=2)
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
        res = (self.unit_price * self.quantity)
        return res.quantize(Decimal('0.0000'))

    @property
    def total_before_tax(self):
        if self.invoice:
            sales_tax_percent = self.invoice.sales_tax_percent
        elif self.proforma:
            sales_tax_percent = self.proforma.sales_tax_percent
        else:
            sales_tax_percent = None

        if not sales_tax_percent:
            return self.total

        initial_unit_price = (self.unit_price * Decimal('100.0000')
                              / (Decimal('100.0000') + sales_tax_percent))
        res = Decimal(self.quantity * initial_unit_price)
        return res.quantize(Decimal('0.0000'))

    @property
    def tax_value(self):
        return self.total - self.total_before_tax

    def __unicode__(self):
        s = "{descr} - {unit} - {unit_price} - {quantity} - {product_code}"
        return s.format(
            descr=self.description,
            unit=self.unit,
            unit_price=self.unit_price,
            quantity=self.quantity,
            product_code=self.product_code)
