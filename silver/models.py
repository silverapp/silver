"""Models for the silver app."""
import datetime
from django.core.validators import EmailValidator
from silver.api.dateutils import last_date_that_fits, next_date_after_period

from django.db import models
from django_fsm import FSMField, transition
from international.models import countries, currencies

INTERVALS = (
    ('day', 'Day'),
    ('week', 'Week'),
    ('month', 'Month'),
    ('year', 'Year')
)

STATES = (
    ('active', 'Active'),
    ('inactive', 'Inactive'),
    ('past_due', 'Past Due'),
    ('on_trial', 'On Trial'),
    ('canceled', 'Canceled'),
    ('ended', 'Ended')
)

UPDATE_TYPES = (
    ('absolute', 'Absolute'),
    ('relative', 'Relative')
)



class Plan(models.Model):
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
        'MeteredFeature',
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


class AddOnFeature(models.Model):
    name = models.CharField(
        max_length=32,
        help_text='The feature display name.'
    )
    plan = models.ForeignKey(
        'Plan',
        help_text="The plan to whom the feature belongs."
    )


class MeteredFeatureUnitsLog(models.Model):
    metered_feature = models.ForeignKey('MeteredFeature')
    subscription = models.ForeignKey('Subscription')
    consumed_units = models.FloatField()
    start_date = models.DateField(editable=False)
    end_date = models.DateField(editable=False)

    class Meta:
        unique_together = ('metered_feature', 'subscription', 'start_date',
                           'end_date')

    def __unicode__(self):
        return self.metered_feature.name


class Subscription(models.Model):
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
            return next_start_date - datetime.timedelta(days=1)
        return None

    @transition(field=state, source=['inactive', 'canceled'], target='active')
    def activate(self):
        self.start_date = datetime.date.today()
        if self.trial_end is None:
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


class Offer(models.Model):
    plans = models.ManyToManyField(
        'Plan',
        help_text="The plans that are included in the customer's offer"
    )

class BillingDetail(models.Model):
    name = models.CharField(
        max_length=128,
        help_text='The name to be used for billing purposes.'
    )
    company = models.CharField(
        max_length=128, blank=True, null=True,
        help_text='Company to issue invoices to.'
    )
    email = models.CharField(max_length=256, validators=[EmailValidator, ])
    address_1 = models.CharField(max_length=128)
    address_2 = models.CharField(max_length=48, blank=True, null=True)
    country = models.CharField(choices=countries, max_length=3,
                               default=countries[0][0])
    city = models.CharField(max_length=128, blank=True, null=True)
    state = models.CharField(max_length=128, blank=True, null=True)
    zip_code = models.CharField(max_length=32, blank=True, null=True)
    extra = models.TextField(
        blank=True, null=True,
        help_text='Extra information to display on the invoice '
                  '(markdown formatted).'
    )

    def __unicode__(self):
        display = self.name
        if self.company:
            display += ' (' + unicode(self.company) + ')'
        return display


class Customer(models.Model):
    customer_reference = models.CharField(
        max_length=256, blank=True, null=True,
        help_text="It's a reference to be passed between silver and clients. "
                  "It usually points to an account ID."
    )
    billing_details = models.OneToOneField(
        'BillingDetail',
        help_text='An hash consisting of billing information. '
        'None are mandatory and all will show up on the invoice.'
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

    offer = models.OneToOneField(
        'Offer', null=True, blank=True,
        help_text="A custom offer consisting of a custom selection of plans."
    )

    def __unicode__(self):
        return self.billing_details.name

class Provider(models.Model):
    pass
