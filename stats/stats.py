from decimal import Decimal

from kombu.utils import json

from silver.models import Transaction, Invoice, Proforma, Subscription, Plan, BillingLog
from datetime import datetime, date, timedelta
from django.utils import timezone

from django.db.models.functions import (ExtractYear, ExtractMonth, ExtractWeekDay, ExtractWeek,
                                        Coalesce)
from django.db.models import Avg, Sum, Count, DecimalField, Subquery, OuterRef
from django.db.models import ExpressionWrapper

from collections import namedtuple


class Stats(object):
    MODIFIER_ANNOTATION = 'modifier'
    granulation_customer = ""
    granulation_currency = ""
    granulation_field = ""

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
                    'created_at': ['year', 'month', 'day'],
                    'currency': []
                }
            }
        },
        'documents': {
            'count': {
                'modifiers': [],
                'granulations': {
                    'issue_date': ['year', 'month', 'day'],
                    'paid_date': ['year', 'month', 'day'],
                    'currency': [],
                    'customer': []
                }
            },
            'amount': {
                'modifiers': [],
                'granulations': {
                    'issue_date': ['year', 'month', 'day'],
                    'paid_date': ['year', 'month', 'day'],
                    'currency': [],
                    'customer': []
                }
            },
            'paid_date': {
                'modifiers': [],
                'granulations': {
                    'paid_date': ['year', 'month', 'day'],
                    'currency': [],
                    'customer': []

                }
            },
            'overdue_payments': {
                'modifiers': [],
                'granulations': {
                    'issued_at': ['year', 'month', 'day'],
                    'paid_date': ['year', 'month', 'day'],
                    'currency': [],
                    'customer': []
                }
            }
        },
        'subscriptions': {
            'estimated_income': {
                'modifiers': ['include_unused_plans', None],
                'granulations': {
                    'plan': [],
                    'currency': [],
                    'customer': []
                }
            }
        }
    }

    def __init__(self, queryset, result_type, modifier=None, granulations=None):
        self.queryset = queryset
        self.result_type = result_type
        self.modifier = modifier
        self.granulations = granulations or []

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
                        if granulation['value'] is not None and granulation['value'] not in \
                                granulation_parameters:
                            raise ValueError("The granulation parameter is incorrect")

        return self.get_result()

    def get_data(self, queryset, modifier_field, granulation_field, time_granulation_interval,
                 additional_granulation_field=None):
        if self.result_type == 'count':
            annotate_with = {self.MODIFIER_ANNOTATION: Count(modifier_field)}
        elif self.result_type == 'amount':
            if self.modifier == 'average':
                annotate_with = {
                    self.MODIFIER_ANNOTATION: ExpressionWrapper(
                        Avg(modifier_field), output_field=DecimalField(decimal_places=2)
                    )
                }
            elif self.modifier == 'total':
                annotate_with = {self.MODIFIER_ANNOTATION: Sum(modifier_field)}

        if additional_granulation_field is not None:
            group_by = [self.MODIFIER_ANNOTATION, additional_granulation_field]
        else:
            group_by = [self.MODIFIER_ANNOTATION]

        queryset = queryset.order_by(). \
            annotate(year=ExtractYear(granulation_field)).values('year')

        if time_granulation_interval == 'year':
            return self.serialize_result(queryset.annotate(**annotate_with).
                                         values('year', *group_by))

        elif time_granulation_interval == 'month':
            return queryset.annotate(month=ExtractMonth(granulation_field)).values('year',
                                                                                   'month').annotate(
                **annotate_with).values('year', 'month', *group_by)

        elif time_granulation_interval == 'week':
            return self.serialize_result(queryset.
                                         annotate(week=ExtractWeek(granulation_field)).
                                         values('year', 'week').
                                         annotate(**annotate_with).
                                         values('year', 'week', *group_by))
        elif granulation_field is None:
            pass

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

        return queryset

    def get_granulations(self):
        granulation_arguments = {}
        for granulation in self.granulations:
            name = granulation['name']
            if ((self.queryset.model == Transaction and name in ['created_at', 'updated_at'])
                or (self.queryset.model == Invoice and name in ['issue_date', 'paid_date'])
                    or (self.queryset.model == Subscription and name == 'plan')):
                granulation_arguments['granulation_field'] = name
                granulation_arguments['time_granulation_interval'] = granulation['value']
            else:
                granulation_arguments['additional_granulation_field'] = name
        if granulation_arguments:
            if self.queryset.model == Invoice and self.result_type != 'count':
                granulation_arguments['granulation_details_field_name'] = 'granulation'
            if self.queryset.model == Subscription:
                granulation_arguments['granulation_details_field_name'] = 'id'
        print granulation_arguments
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

    def documents_overdue_payments(self, queryset):
        overdue = []
        for i in queryset.filter(due_date__lte=datetime.now(), state=Invoice.STATES.ISSUED):
            name = i.customer.first_name + " " + i.customer.last_name
            new_document = {'customer':  name,
                            'due_date': i.due_date,
                            'total': i.total,
                            'paid': i.amount_paid_in_transaction_currency,
                            'left': i.amount_to_be_charged_in_transaction_currency
                            }
            overdue.append(new_document)
        return overdue

    def _numbers_to_strings(self, argument):
        switcher = {
            1: "Jan",
            2: "Feb",
            3: "Mar",
            4: "Apr",
            5: "May",
            6: "Jun",
            7: "Jul",
            8: "Aug",
            9: "Sep",
            10: "Oct",
            11: "Nov",
            12: "Dec",
        }
        return switcher.get(argument, "none")

    def _create_data(self, currency, id, customer_name,
                     amount, granulation_arguments, granulation_details):
        if not granulation_arguments:
            data = {'granulations': {
                'currency': currency
            },
                'values': [{
                    'id': id,
                    'estimated_income': amount,
                    'customer': customer_name
                }]
            }
        else:
            data = {'granulations': {
                'currency': currency
            },
                'values': [{
                    'id': id
                }]
            }
            if 'granulation_field' in granulation_arguments:
                data['granulations'][granulation_arguments['granulation_field']] = {
                    'value': granulation_details['granulation_value'],
                    granulation_arguments['granulation_details_field_name']: granulation_details[
                        'granulation_details_value']
                }
            if 'additional_granulation_field' in granulation_arguments:
                data['granulations']['customer'] = customer_name
            else:
                data['values'][0]['customer'] = customer_name
            if amount is not None:
                data['values'][0]['estimated_income'] = amount

        return data

    def _add_estimated_income_to_list(self, stats_list, currency, id, customer_name,
                                      amount, granulation_arguments, granulation_details):
        if 'additional_granulation_field' in granulation_arguments:
            if 'granulation_value' in granulation_details:
                if self.granulation_customer != customer_name:
                    data = self._create_data(currency, id, customer_name, amount,
                                             granulation_arguments,
                                             granulation_details)
                    stats_list.append(data)
                    self.granulation_field =  ['granulation_value']
                    self.granulation_customer = customer_name
                    self.granulation_currency = currency

                elif self.granulation_field != granulation_details['granulation_value']:
                    data = self._create_data(currency, id, customer_name, amount,
                                             granulation_arguments,
                                             granulation_details)
                    stats_list.append(data)
                    self.granulation_currency = currency
                    self.granulation_field = granulation_details['granulation_value']

                elif self.granulation_currency != currency:
                    data = self._create_data(currency, id, customer_name, amount,
                                             granulation_arguments,
                                             granulation_details)
                    stats_list.append(data)
                    self.granulation_currency = currency

                else:
                    stats_list[len(stats_list) - 1]['values'].append(
                        {
                            'id': id,
                            'estimated_income': amount,
                            'customer': customer_name
                        }
                    )
            else:
                if self.granulation_customer != customer_name:
                    data = self._create_data(currency, id, customer_name, amount,
                                             granulation_arguments,
                                             granulation_details)
                    stats_list.append(data)
                    self.granulation_currency = currency
                    self.granulation_customer = customer_name

                elif self.granulation_currency != currency:
                    data = self._create_data(currency, id, customer_name, amount,
                                             granulation_arguments,
                                             granulation_details)
                    stats_list.append(data)
                    self.granulation_currency = currency

                else:
                    stats_list[len(stats_list) - 1]['values'].append(
                        {
                            'id': id,
                            'estimated_income': amount,
                        }
                    )

        elif 'granulation_value' in granulation_details:
            if self.granulation_field != granulation_details['granulation_value']:
                data = self._create_data(currency, id, customer_name, amount, granulation_arguments,
                                         granulation_details)
                stats_list.append(data)
                self.granulation_currency = currency
                self.granulation_field = granulation_details['granulation_value']

            elif self.granulation_currency != currency:
                data = self._create_data(currency, id, customer_name, amount, granulation_arguments,
                                         granulation_details)
                stats_list.append(data)
                self.granulation_currency = currency

            else:
                stats_list[len(stats_list) - 1]['values'].append(
                    {
                        'id': id,
                        'customer_name': customer_name
                    }
                )
                values_last_position = len(stats_list[len(stats_list) - 1]['values']) - 1
                if amount is not None:
                    stats_list[len(stats_list) - 1]['values'][values_last_position]['estimated_income'] = amount

        else:
            if self.granulation_currency != currency:
                data = self._create_data(currency, id, customer_name, amount, granulation_arguments,
                                         granulation_details)
                stats_list.append(data)
                self.granulation_currency = currency

            else:
                stats_list[len(stats_list) - 1]['values'].append(
                    {
                        'id': id,
                        'customer_name': customer_name
                    }
                )
                if amount is not None:
                    stats_list[len(stats_list) - 1]['values'][0]['estimated_income'] = amount

    def _group_stats_fields(self, group_by, granulation_arguments, granulation_details,
                            granulation_field, currency):
        if len(granulation_arguments) != 0:
            if 'granulation_field' in granulation_arguments:
                group_by = [currency, granulation_field, 'customer__first_name',
                            'customer__last_name'] + group_by
            if 'additional_granulation_field' in granulation_arguments and \
                            granulation_arguments['additional_granulation_field'] == 'customer':
                group_by = ['customer__first_name', 'customer__last_name', granulation_field,
                            currency] + group_by
        else:
            group_by = [currency, granulation_field, 'customer__first_name',
                        'customer__last_name'] + group_by

        if 'time_granulation_interval' in granulation_arguments:
            granulation_details['granulation_details_value'] = granulation_arguments[
                'time_granulation_interval']

        return group_by

    def subscriptions_estimated_income(self, queryset):
        stats_list = []
        group_by = ['subscription_amount', 'id', 'plan__name']
        granulation_details = {}
        granulation_arguments = self.get_granulations()

        group_by = self._group_stats_fields(group_by, granulation_arguments, granulation_details,
                                            granulation_field='plan_id', currency='plan__currency')

        last_month = timezone.now() - timedelta(days=60)
        entries = BillingLog.objects.filter(billing_date__gt=last_month,
                                            subscription_id=OuterRef('pk')) \
            .order_by() \
            .values('subscription_id') \
            .annotate(sum=Sum('total')) \
            .values('sum')

        subscriptions = queryset.annotate(
            subscription_amount=Coalesce(ExpressionWrapper(
                Subquery(entries),
                output_field=DecimalField(decimal_places=2)
            ), Decimal('0.00'))
        ).values(*group_by).filter(subscription_amount__gt=0).order_by(*group_by)

        current_customer = None
        for subscription in subscriptions:

            customer_name = subscription['customer__first_name'] + " " + \
                            subscription['customer__last_name']
            granulation_details['granulation_value'] = subscription['plan__name']
            granulation_details['granulation_details_value'] = subscription['plan_id']

            self._add_estimated_income_to_list(stats_list, subscription['plan__currency'],
                                               subscription['id'], customer_name,
                                               subscription['subscription_amount'],
                                               granulation_arguments, granulation_details
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

    def _get_time_granulations(self, document, granulation_arguments, granulation_field, granulation_details):
        if 'time_granulation_interval' in granulation_arguments and 'time_granulation_interval' is not None:
            if granulation_arguments['time_granulation_interval'] == 'year':
                granulation_details['granulation_value'] = str(
                    getattr(document, granulation_field).year)
            elif granulation_arguments['time_granulation_interval'] == 'month':
                month = self._numbers_to_strings(getattr(document, granulation_field).month)
                granulation_details['granulation_value'] = str(
                    getattr(document, granulation_field).year) + ' ' + month
            elif granulation_arguments['time_granulation_interval'] == 'day':
                month = self._numbers_to_strings(
                    getattr(document, granulation_field).month) + ' ' + str(
                    getattr(document, granulation_field).day)
                granulation_details['granulation_value'] = str(
                    getattr(document, granulation_field).year) + ' ' + month


    # #########################################################################

    def documents_amount(self, queryset):
        group_by = []
        granulation_details = {}
        granulation_arguments = self.get_granulations()
        granulation_field = granulation_arguments['granulation_field']
        doc = dict()
        key = None

        group_by = self._group_stats_fields(group_by, granulation_arguments, granulation_details,
                                           granulation_field, currency='currency')

        dictionary = {granulation_field + '__isnull': True}
        name_tuple = namedtuple("group_by", ["currency", "name", "issue_date"])

        for document in queryset.filter(id__gte=3000).exclude(**dictionary).filter(customer__first_name__icontains='Vlad').order_by(*group_by):
            customer_name = document.customer.first_name + " " + document.customer.last_name
            self._get_time_granulations(document, granulation_arguments, granulation_field, granulation_details)

            if granulation_arguments['granulation_field'] is not None:
                if granulation_arguments['additional_granulation_field'] is not None:

                    item = name_tuple(issue_date=granulation_details['granulation_value'], name=customer_name, currency=document.currency)
                    search_document = doc.get(item, [])

                    if not search_document:
                        if key is not None:
                            data = {
                                'customer_name': key.name,
                                'currency': key.currency,
                                'issue_date': key.issue_date
                            }
                            data['values'] = []

                            for item in doc[key]:
                                data['values'].append(item)

                            yield data

                        key = name_tuple(issue_date=granulation_details['granulation_value'], name=customer_name, currency=document.currency)


                    doc[key] = search_document + [{'id': document.id, 'total': document.total}]

            elif granulation_arguments['additional_granulation_field'] is not None:

                search_document = document.get((document.currency, customer_name), [])

    def documents_amount_old(self, queryset):
        stats_list = []
        group_by = []
        granulation_details = {}
        granulation_arguments = self.get_granulations()
        granulation_field = granulation_arguments['granulation_field']

        group_by = self._group_stats_fields(group_by, granulation_arguments, granulation_details,
                                            granulation_field, currency='currency')

        dict = {granulation_field + '__isnull': True}

        for document in queryset.filter(id__gte=3000).exclude(**dict). \
                order_by(*group_by):
            self._get_time_granulations(document, granulation_arguments, granulation_field, granulation_details)

            customer_name = document.customer.first_name + " " + document.customer.last_name

            self._add_estimated_income_to_list(stats_list, document.currency, document.id, customer_name, document.total,
                                               granulation_arguments, granulation_details)
        return stats_list

    def documents_paid_date(self, queryset):
        stats_list = []
        group_by = []
        granulation_details = {}
        granulation_arguments = self.get_granulations()
        granulation_field = granulation_arguments['granulation_field']

        group_by = self._group_stats_fields(group_by, granulation_arguments, granulation_details,
                                            granulation_field, currency='currency')

        dict = {granulation_field + '__isnull': True}

        for document in queryset.filter(id__gte=3000).exclude(**dict). \
                order_by(*group_by):
            self._get_time_granulations(document, granulation_arguments, granulation_field, granulation_details)
            customer_name = document.customer.first_name + " " + document.customer.last_name

            self._add_estimated_income_to_list(stats_list, document.currency, document.id, customer_name, None,
                                               granulation_arguments, granulation_details)
        return stats_list

    def _get_model_name(self):
        if self.queryset.model == Transaction:
            return 'transactions'
        elif self.queryset.model == Invoice or self.queryset.model == Proforma:
            return 'documents'
        elif self.queryset.model == Subscription:
            return 'subscriptions'

    def get_result(self):
        if self.modifier is not None:
            method_name = self._get_model_name() + '_' + self.result_type + '_' + self.modifier
            method = getattr(self, method_name)
            return method(self.queryset)
        else:
            method_name = self._get_model_name() + '_' + self.result_type
            method = getattr(self, method_name)
            return method(self.queryset)

