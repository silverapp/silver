from decimal import Decimal

from silver.models import Transaction, Invoice, Proforma, Subscription, Plan, BillingLog
from datetime import datetime, date, timedelta
from django.utils import timezone

from django.db.models.functions import (ExtractYear, ExtractMonth, ExtractWeekDay, ExtractWeek,
                                        Coalesce)
from django.db.models import Avg, Sum, Count, DecimalField, Subquery, OuterRef
from django.db.models import ExpressionWrapper


class Stats(object):
    MODIFIER_ANNOTATION = 'modifier'

    result_types = {
        'transactions': {
            'count': {
                'modifiers': [],
                'granulations': {
                    'created_at': ['year', 'month', 'week', 'day'],
                    'currency': []
                }
            },
            'amount': {
                'modifiers': ['average', 'total'],
                'granulations': {
                    'created_at': ['year', 'month', 'week', 'day'],
                    'currency': []
                }
            }
        },
        'documents': {
            'count': {
                'modifiers': [],
                'granulations': {
                    'issue_date': ['year', 'month', 'week', 'day'],
                    'paid_at': ['year', 'month', 'week', 'day'],
                    'currency': []
                }
            },
            # not implemented yet
            'paid_date': {
                'modifiers': ['average'],
                'granulations': {
                    'issue_date': ['year', 'month', 'week', 'day'],
                    'paid_at': ['year', 'month', 'week', 'day'],
                    'currency': []
                }
            },
            'overdue_payments': {
                'modifiers': [],
                'granulations': {
                    'issued_at': ['year', 'month', 'week', 'day'],
                    'paid_at': ['year', 'month', 'week', 'day'],
                    'currency': []
                }
            }
        },
        # not tested
        'billing': {
            'amount': {
                'modifiers': ['average', 'total'],
                'granulations': {
                    'billing_date': ['year', 'month', 'week', 'day'],
                }
            }
        },
        'subscriptions': {
            'estimated_income': {
                'modifiers': ['include_unused_plans', None],
                'granulations': {
                    'billing_period': ['year', 'month'],
                    'plan': None
                }
            }
        }
    }

    def validate(self):
        if self.queryset.model != Transaction and self.queryset.model != Invoice \
                and self.queryset.model != Subscription and self.queryset.model != BillingLog:
            raise ValueError('Invalid model, choices are: Transaction, Invoice, Subscription, '
                             'BillingLog')
        if self.result_type is None:
            raise ValueError('Select a result type: choices are: amount, count, overdue_payments, '
                             'estimated_income')

        for model, metrics in self.result_types.iteritems():
            if model != self._get_model_name():
                continue
            if self.result_type not in metrics:
                raise ValueError('Invalid result type')
            for result_type, values in metrics.iteritems():
                if result_type == self.result_type:
                    if not values['modifiers']:
                        if self.modifier is not None:
                            raise ValueError("The result type doesn't have modifiers")
                    elif None not in values['modifiers'] and self.modifier is None:
                        raise ValueError('The modifier argument is required.')
                    elif self.modifier not in values['modifiers']:
                        raise ValueError('Invalid modifier')
                else:
                    continue
                for granulation in self.granulations:
                    if granulation['name'] not in values['granulations']:
                        raise ValueError("The granulation field is incorrect")
                for granulation_field, granulation_parameters in values['granulations'].iteritems():
                    if not granulation_parameters:
                        continue
                    for granulation in self.granulations:
                        if granulation['value'] is not None and granulation['value'] not in granulation_parameters:
                            raise ValueError("The granulation parameter is incorrect")

        return self.get_result()

    def __init__(self, queryset, result_type, modifier=None, granulations=None):
        self.queryset = queryset
        self.result_type = result_type
        self.modifier = modifier
        self.granulations = granulations or []

    def get_data(self, queryset, modifier_field, time_granulation_field, time_granulation_interval,
                 additional_granulation_field=None):
        if self.result_type == 'count':
            annotate_with = {self.MODIFIER_ANNOTATION: Count(modifier_field)}
        elif self.result_type == 'amount':
            if self.modifier == 'average':
                annotate_with = {self.MODIFIER_ANNOTATION:
                                     ExpressionWrapper(Avg(modifier_field),
                                                       output_field=DecimalField(decimal_places=2))}
            elif self.modifier == 'total':
                annotate_with = {self.MODIFIER_ANNOTATION: Sum(modifier_field)}

        if additional_granulation_field is not None:
            group_by = [self.MODIFIER_ANNOTATION, additional_granulation_field]
        else:
            group_by = [self.MODIFIER_ANNOTATION]

        queryset = queryset.order_by(). \
            annotate(year=ExtractYear(time_granulation_field)).values('year')

        if time_granulation_interval == 'year':
                return self.serialize_result(queryset.annotate(**annotate_with).
                                             values('year', *group_by))

        elif time_granulation_interval == 'month':
            return self.serialize_result(queryset.
                                         annotate(month=ExtractMonth(time_granulation_field)).
                                         values('year', 'month').
                                         annotate(**annotate_with).
                                         values('year', 'month', *group_by))

        elif time_granulation_interval == 'week':
            return self.serialize_result(queryset.
                                         annotate(week=ExtractWeek(time_granulation_field)).
                                         values('year', 'week').
                                         annotate(**annotate_with).
                                         values('year', 'week', *group_by))
        elif time_granulation_field is None:
            pass

    def get_granulations(self):
        granulation_arguments = {}
        for granulation in self.granulations:
            name = granulation['name']
            if ((self.queryset.model == Transaction and name in ['created_at', 'updated_at'])
                    or (self.queryset.model == Invoice and name in ['issue_date', 'paid_date'])
                    or (self.queryset.model == BillingLog and name == 'billing_date' )):
                        granulation_arguments['time_granulation_field'] = name
                        granulation_arguments['time_granulation_interval'] = granulation['value']
            else:
                granulation_arguments['additional_granulation_field'] = name
        return granulation_arguments

    def transactions_count(self, queryset):
        granulation_arguments = self.get_granulations()
        modifier_field = 'id'
        return self.get_data(queryset, modifier_field, **granulation_arguments)

    def transactions_amount_average(self, queryset):
        granulation_arguments = self.get_granulations()
        modifier_field = 'amount'
        return self.get_data(queryset, modifier_field, **granulation_arguments)

    def transactions_amount_total(self, queryset):
        granulation_arguments = self.get_granulations()
        modifier_field = 'amount'
        return self.get_data(queryset, modifier_field=modifier_field, **granulation_arguments)

    def documents_count(self, queryset):
        granulation_arguments = self.get_granulations()
        modifier_field = 'id'
        return self.get_data(queryset, modifier_field, **granulation_arguments)

    # set default value 0 if the fields do not exist
    def documents_overdue_payments(self, queryset):
        overdue = {}
        for i in queryset.filter(due_date__lte=datetime.now()):
            new = {i.customer: [{'total': i.total, 'paid': i.amount_paid_in_transaction_currency,
                                 'left': i.amount_to_be_charged_in_transaction_currency}]}
            overdue[i.customer_id] = new
        return overdue

    # fix this
    def billing_amount_average(self, queryset):
        granulation_arguments = self.get_granulations()
        modifier_field = 'total'
        return self.get_data(queryset, modifier_field, **granulation_arguments)

    # fix this
    def billing_amount_total(self, queryset):
        granulation_arguments = self.get_granulations()
        modifier_field = 'total'
        return self.get_data(queryset, modifier_field=modifier_field, **granulation_arguments)

    def serialize_result(self, queryset):
        tupleList = []
        additional_granulation = self.get_granulations().get('additional_granulation_field')
        for i in queryset:
            timestamp_date = date(
                year=i['year'], month=i.get('month', 1), day=i.get('day', 1)
            )

            if i.get('week'):
                timestamp_date += timedelta(days=i['week'] * 7 - 1)
            timestamp = timestamp_date.strftime('%s')

            datapoint = ((timestamp, i[self.MODIFIER_ANNOTATION])
                         if additional_granulation is None
                         else (timestamp, i[additional_granulation],
                               i[self.MODIFIER_ANNOTATION]))
            tupleList.append(datapoint)

        return tupleList

    def _add_estimated_income_to_list(self, stats_list, plan_name, plan_id, subscription_id,
                                      subscription_amount, customer):
        data = {'granulations': {
            'plan': {
                'name': plan_name,
                'id': plan_id
            }},
            'values': [
                {
                    'subscription_id': subscription_id,
                    'estimated_income': subscription_amount,
                    'customer_name': customer
                }
            ]
        }
        stats_list.append(data)

    def subscriptions_estimated_income(self, queryset):
        last_month = timezone.now() - timedelta(days=31)
        entries = BillingLog.objects.filter(billing_date__gt=last_month,
                                            subscription_id=OuterRef('pk'))\
                                    .order_by()\
                                    .values('subscription_id')\
                                    .annotate(sum=Sum('total'))\
                                    .values('sum')

        subscriptions = queryset.annotate(
            subscription_amount=Coalesce(ExpressionWrapper(
                Subquery(entries),
                output_field=DecimalField(decimal_places=2)
            ), Decimal('0.00'))
        ).values(
            'subscription_amount', 'id', 'plan', 'plan__name', 'customer__first_name',
            'customer__last_name'
        ).order_by('-subscription_amount')

        stats_list = []
        for subscription in subscriptions:
            if not stats_list:
                self._add_estimated_income_to_list(
                    stats_list, subscription['plan__name'], subscription['plan'],
                    subscription['id'], subscription['subscription_amount'],
                    subscription['customer__first_name'] + " " + subscription['customer__last_name']
                )
            else:
                found = 0
                for list_item in stats_list:
                    for modifier, modifier_values in list_item.iteritems():
                        if modifier == 'granulations':
                            for plan, plan_details in modifier_values.iteritems():
                                if plan_details['name'] == subscription['plan__name']:
                                    list_item['values'].append(
                                        {
                                            'subscription_id': subscription['id'],
                                            'estimated_income': subscription['subscription_amount'],
                                            'customer_name':
                                                subscription['customer__first_name'] + " " +
                                                subscription['customer__last_name']
                                        }
                                    )
                                    found = 1
                if found == 0:
                    self._add_estimated_income_to_list(
                        stats_list, subscription['plan__name'], subscription['plan'],
                        subscription['id'], subscription['subscription_amount'],
                        subscription['customer__first_name'] + " " +
                        subscription['customer__last_name']
                    )
        return stats_list

    def subscriptions_estimated_income_include_unused_plans(self, queryset):
        stats_list = self.subscriptions_estimated_income(queryset)
        for i in Plan.objects.exclude(subscription__isnull=False).distinct().filter(id=1):
            data = {'granulations': {
                'plan': {
                    'name': i.name,
                    'id': i.id
                }},
                'values': []
            }
            stats_list.append(data)
        return stats_list

    def _get_model_name(self):
        if self.queryset.model == Transaction:
            return 'transactions'
        elif self.queryset.model == Invoice or self.queryset.model == Proforma:
            return 'documents'
        elif self.queryset.model == Subscription:
            return 'subscriptions'
        elif self.queryset.model == BillingLog:
            return 'billing'

    def get_result(self):
        if self.modifier is not None:
            method_name = self._get_model_name() + '_' + self.result_type + '_' + self.modifier
            method = getattr(self, method_name)
            return method(self.queryset)
        else:
            method_name = self._get_model_name() + '_' + self.result_type
            method = getattr(self, method_name)
            return method(self.queryset)
