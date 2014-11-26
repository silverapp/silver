"""Models for the silver app."""
import datetime

from django.core.exceptions import ValidationError
from django.db import models
from django_fsm import FSMField, transition
from international.models import countries, currencies
from livefield.models import LiveModel

from silver.api.dateutils import last_date_that_fits, next_date_after_period
from silver.utils import get_object_or_None


UPDATE_TYPES = (
    ('absolute', 'Absolute'),
    ('relative', 'Relative')
)


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
    amount = models.FloatField(
        help_text='The amount in the specified currency to be charged on the '
                  'interval specified.'
    )
    currency = models.CharField(
        choices=currencies, max_length=4, default=currencies[0][0],
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
    due_days = models.PositiveIntegerField(
        help_text='Due days for generated invoice.'
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
    product_code = models.CharField(max_length=128, unique=True,
                                    help_text='The product code for this plan.')
    provider = models.ForeignKey(
        'Provider', related_name='plans',
        help_text='The provider which provides the plan.'
    )

    def __unicode__(self):
        return self.name


class MeteredFeature(models.Model):
    name = models.CharField(
        max_length=32,
        help_text='The feature display name.'
    )
    price_per_unit = models.FloatField(help_text='The price per unit.')
    included_units = models.FloatField(
        help_text='The number of included units per plan interval.'
    )

    def __unicode__(self):
        return self.name


class MeteredFeatureUnitsLog(models.Model):
    metered_feature = models.ForeignKey('MeteredFeature')
    subscription = models.ForeignKey('Subscription')
    consumed_units = models.FloatField()
    start_date = models.DateField(editable=False)
    end_date = models.DateField(editable=False)

    class Meta:
        unique_together = ('metered_feature', 'subscription', 'start_date',
                           'end_date')

    def clean(self):
        super(MeteredFeatureUnitsLog, self).clean()
        if not self.id:
            start_date = self.subscription.current_start_date
            end_date = self.subscription.current_end_date
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
            self.start_date = self.subscription.current_start_date
            self.end_date = self.subscription.current_end_date
            super(MeteredFeatureUnitsLog, self).save()
        else:
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
        ('past_due', 'Past Due'),
        ('on_trial', 'On Trial'),
        ('canceled', 'Canceled'),
        ('ended', 'Ended')
    )

    plan = models.ForeignKey(
        'Plan',
        help_text='The plan the customer is subscribed to.'
    )
    customer = models.ForeignKey(
        'Customer',
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

    @property
    def current_start_date(self):
        return last_date_that_fits(
            initial_date=self.start_date,
            end_date=datetime.date.today(),
            interval_type=self.plan.interval,
            interval_count=self.plan.interval_count
        )

    @property
    def current_end_date(self):
        next_start_date = next_date_after_period(
            initial_date=self.current_start_date,
            interval_type=self.plan.interval,
            interval_count=self.plan.interval_count
        )
        if next_start_date:
            ced = next_start_date - datetime.timedelta(days=1)
            if self.ended_at:
                if self.ended_at < ced:
                    return self.ended_at
            else:
                return ced
        return None

    @transition(field=state, source=['inactive', 'canceled'], target='active')
    def activate(self, start_date=None, trial_end_date=None):
        if start_date:
            self.start_date = start_date
        elif self.start_date is None:
            self.start_date = datetime.date.today()

        if trial_end_date:
            self.trial_end = trial_end_date
        elif self.trial_end is None:
            self.trial_end = self.start_date + datetime.timedelta(
                days=self.plan.trial_period_days
            )

    @transition(field=state, source=['active', 'past_due', 'on_trial'],
                target='canceled')
    def cancel(self):
        pass

    @transition(field=state, source='canceled', target='ended')
    def end(self):
        self.ended_at = datetime.date.today()

    def __unicode__(self):
        return '%s (%s)' % (self.customer, self.plan)


class BillingEntity(LiveModel):
    name = models.CharField(
        max_length=128, blank=True, null=True,
        help_text='The name to be used for billing purposes.'
    )
    company = models.CharField(max_length=128)
    email = models.EmailField(max_length=254, blank=True, null=True)
    address_1 = models.CharField(max_length=128)
    address_2 = models.CharField(max_length=48, blank=True, null=True)
    country = models.CharField(choices=countries, max_length=3)
    city = models.CharField(max_length=128)
    state = models.CharField(max_length=128, blank=True, null=True)
    zip_code = models.CharField(max_length=32)
    extra = models.TextField(
        blank=True, null=True,
        help_text='Extra information to display on the invoice '
                  '(markdown formatted).'
    )

    class Meta:
        abstract = True

    def __unicode__(self):
        display = self.name
        if self.company:
            display = '%s (%s)' % (display, self.company)
        return display


class Customer(BillingEntity):
    customer_reference = models.CharField(
        max_length=256, blank=True, null=True,
        help_text="It's a reference to be passed between silver and clients. "
                  "It usually points to an account ID."
    )
    sales_tax_percent = models.FloatField(
        null=True,
        help_text="Whenever to add sales tax. "
                  "If null, it won't show up on the invoice."
    )
    sales_tax_name = models.CharField(
        max_length=64, help_text="Sales tax name (eg. 'sales tax' or 'VAT')."
    )
    consolidated_billing = models.BooleanField(
        default=False, help_text='A flag indicating consolidated billing.'
    )

    def __init__(self, *args, **kwargs):
        super(Customer, self).__init__(*args, **kwargs)
        company_field = self._meta.get_field_by_name("company")[0]
        company_field.help_text = "The company to which the bill is issued."

    def __unicode__(self):
        return " - ".join(filter(None, [self.name, self.company]))

    def complete_address(self):
        return ", ".join(filter(None, [self.address_1, self.city, self.state,
                                       self.zip_code, self.country]))
    complete_address.short_description = 'Complete address'


class Provider(BillingEntity):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        company_field = self._meta.get_field_by_name("company")[0]
        company_field.help_text = "The provider issuing the invoice."

    def __unicode__(self):
        return " - ".join(filter(None, [self.name, self.company]))


class ProductCode(models.Model):
    value = models.CharField(max_length=128, unique=True)


class CustomerHistory(BillingEntity):
    customer = models.ForeignKey('Customer', related_name='archived_entries')


class ProviderHistory(BillingEntity):
    provider = models.ForeignKey('Provider', related_name='archived_entries')


class Invoice(models.Model):
    states = ['draft', 'issued', 'paid', 'canceled', 'past_due']
    STATE_CHOICES = tuple((state, ' '.join(state.split('_')).title())
                          for state in states)

    due_date = models.DateField(null=True, blank=True)
    issue_date = models.DateField(null=True, blank=True)
    paid_date = models.DateField(null=True, blank=True)
    cancel_date = models.DateField(null=True, blank=True)
    customer = models.ForeignKey('CustomerHistory', related_name='invoices')
    provider = models.ForeignKey('Provider', related_name='invoices')
    """
    customer = models.ForeignKey('Customer', related_name='invoices')
    provider = models.ForeignKey('Provider', related_name='invoices')
    final_customer = models.ForeignKey('BillingDetailsHistory',
                                       null=True, blank=True, related_name='fc')
    final_provider = models.ForeignKey('BillingDetailsHistory',
                                       null=True, blank=True, related_name='fp')
    """
    sales_tax_percent = models.DecimalField(max_digits=5, decimal_places=2,
                                            null=True, blank=True)
    sales_tax_name = models.CharField(max_length=10, blank=True, null=True)
    currency = models.CharField(
        choices=currencies, max_length=4, null=False, blank=False,
        help_text='The currency used for billing.'
    )
    state = FSMField(
        choices=STATE_CHOICES, max_length=10, default=states[0],
        verbose_name='Invoice state',
        help_text='The state the invoice is in.'
    )

    @transition(field=state, source='draft', target='issued')
    def issue_invoice():
        pass

    def customer_display(self):
        if self.final_customer:
            list_display_fields = ['company', 'email', 'address_1', 'city',
                                   'country', 'zip_code']
            fields = [getattr(self.final_customer, field)
                      for field in list_display_fields]
            return ', '.join(fields)
        return ''

    customer_display.short_description = 'Customer'

    def provider_display(self):
        if self.final_provider:
            list_display_fields = ['company', 'email', 'address_1', 'city',
                                   'country', 'zip_code']
            fields = [getattr(self.final_provider, field)
                      for field in list_display_fields]
            return ', '.join(fields)
        return ''

    provider_display.short_description = 'Provider'


class InvoiceEntry(models.Model):
    description = models.CharField(max_length=255)
    unit = models.CharField(max_length=20)
    quantity = models.DecimalField(max_digits=28, decimal_places=10)
    unit_price = models.DecimalField(max_digits=28, decimal_places=10)
    product_code = models.ForeignKey('ProductCode')
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    prorated = models.BooleanField(default=False)
    invoice = models.ForeignKey('Invoice', related_name='entries')
