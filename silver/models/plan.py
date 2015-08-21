from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.db import models
from django.core.validators import MinValueValidator
from international.models import currencies
from dateutil.relativedelta import *
from model_utils import Choices


class Plan(models.Model):
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

    def __unicode__(self):
        return self.name

    @property
    def provider_flow(self):
        return self.provider.flow
