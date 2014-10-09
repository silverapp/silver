"""Models for the silver app."""
from django.db import models
from django.contrib.auth.models import User

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


class Plan(models.Model):
    interval = models.CharField(choices=INTERVALS, max_length=12)
    interval_count = models.PositiveIntegerField()
    amount = models.FloatField()
    currency = models.CharField(max_length=16)
    name = models.CharField(max_length=20)
    trial_period_days = models.PositiveIntegerField(null=True)
    metered_features = models.ForeignKey('MeteredFeature')
    due_days = models.PositiveIntegerField()
    generate_after = models.PositiveIntegerField(default=0)


class MeteredFeature(models.Model):
    name = models.CharField(max_length=16)
    price_per_unit = models.FloatField()
    included_units = models.FloatField()


class Subscription(models.Model):
    plan = models.ForeignKey('Plan')
    customer = models.ForeignKey('Customer')
    trial_end = models.DateTimeField(null=True)
    start_date = models.DateTimeField()
    ended_at = models.DateTimeField(null=True)
    state = models.CharField(choices=STATES, max_length=12,
                             default=STATES[0][0]
    )


class Customer(models.Model):
    customer_reference = models.CharField(max_length=16)
    billing_details = models.OneToOneField(User)
    sales_tax_percent = models.FloatField(null=True)
    sales_tax_name = models.CharField(max_length=16)
    consolidated_billing = models.BooleanField(default=False)
