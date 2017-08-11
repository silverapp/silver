from decimal import Decimal

from silver.models import Transaction, Invoice, Proforma, MeteredFeatureUnitsLog, Subscription, \
    Plan, BillingLog
from datetime import datetime, date, timedelta
from django.db.models.functions import ExtractYear, ExtractMonth, ExtractWeekDay, ExtractWeek, \
    Coalesce
from django.db.models import Avg, Sum, Count, DecimalField, F, Case, When, Max, Subquery, OuterRef
from django.db.models import ExpressionWrapper

{
    'granulations': [
        {
            'name': 'time',
            'value': 'month'
        },
        {
            'name': 'currency'
        }
    ]
}


class Stats(object):
    MODIFIER_ANNOTATION = 'modifier'

    result_types = {
        'transactions': {
            'count': {
                'modifiers': [],
                'granulations': {
                    'created_at': ['year', 'month', 'week', 'day'],
                    'currency': None
                }
            },
            'amount': {
                'modifiers': ['average', 'total'],
                'granulation': ['year', 'month', 'week', 'day', 'none'],
                'currency': None
            }
        },
        'documents': {
            'count': {
                'modifiers': [],
                'granulations': {
                    'issued_at': ['year', 'month', 'week', 'day'],
                    'paid_at': ['year', 'month', 'week', 'day'],
                    'currency': None
                }
            },
            'amount': {
                'modifiers': ['average', 'total'],
                'granulations': {
                    'issued_at': ['year', 'month', 'week', 'day'],
                    'paid_at': ['year', 'month', 'week', 'day'],
                    'currency': None
                }
            },
            'paid_date': {
                'modifiers': ['average'],
                'granulations': {
                    'issued_at': ['year', 'month', 'week', 'day'],
                    'paid_at': ['year', 'month', 'week', 'day'],
                    'currency': None
                }
            },
            'overdue_payments': {
                'modifiers': [],
                'granulations': {
                    'issued_at': ['year', 'month', 'week', 'day'],
                    'paid_at': ['year', 'month', 'week', 'day'],
                    'currency': None
                }
            }
        },
        'subscriptions': {
                'modifiers': ['include_unused_plans'],
                'granulations': {
                    'plan': None,
                    'month': ['Jan']
                }
            }
    }

    def validate(self):
        if self.queryset.model != Transaction and self.queryset.model != Invoice:
            raise ValueError('invalid model!')
        if self.queryset.model == Invoice:
            model = 'documents'
        elif self.queryset.model == Transaction:
            model = 'transactions'
        if self.result_type is None:
            raise ValueError('Select a result type!')

        for key, value in self.result_types.iteritems():
            if key != model:
                continue
            if self.result_type not in value:
                raise ValueError('Invalid result type!')
            for result_type, values in value.iteritems():
                if result_type == self.result_type:
                    if self.granulations['value'] not in values:
                        raise ValueError('Invalid granulation!')
                    elif not values['modifiers']:
                        if self.modifier is not None:
                            raise ValueError("This result type doesn't have modifiers!")
                    elif self.modifier is None:
                            raise ValueError('Select a modifier!')
                    elif self.modifier not in values['modifiers']:
                        raise ValueError('Invalid modifier')
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
                or (self.queryset.model == Invoice and name in ['issue_date', 'paid_date'])):
                granulation_arguments['time_granulation_field'] = name
                granulation_arguments['time_granulation_interval'] = granulation['value']
            else:
                granulation_arguments['additional_granulation_field'] = name
            print ("aici: %s" % granulation_arguments)
        return granulation_arguments

    def transactions_count(self, queryset):
        granulation_arguments = self.get_granulations()
        modifier_field = 'id'
        return self.get_data(queryset, modifier_field, **granulation_arguments)

    def documents_count(self, queryset):
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

    def serialize_result(self, queryset):
        tupleList = []

        additional_granulation = self.get_granulations().get('additional_granulation_field')

        for i in queryset:
            timestamp_date = date(
                year=i['year'], month=i.get('month', 1), day=i.get('day', 1)
            )

            if i.get('week'):
                timestamp_date += timedelta(days=i['week'] * 7 - 1)
                print(i['week'], timedelta(days=i['week'] * 7 - 1))

            timestamp = timestamp_date.strftime('%s')

            datapoint = ((timestamp, i[self.MODIFIER_ANNOTATION])
                         if additional_granulation is None
                         else (timestamp, i[additional_granulation],
                               i[self.MODIFIER_ANNOTATION]))
            tupleList.append(datapoint)

        return tupleList

    def documents_overdue_payments(self, queryset):
        overdue = {}
        for i in queryset.filter(due_date__lte=datetime.now()):
            new = {i.customer: [{'total': i.total, 'paid': i.amount_paid_in_transaction_currency,
                                 'left': i.amount_to_be_charged_in_transaction_currency}]}
            overdue[i.customer_id] = new
        return overdue

    def subscriptions_estimated_income(self, queryset):
        entries = BillingLog.objects.filter(subscription_id=OuterRef('pk')).order_by().\
        values('subscription_id').annotate(sum=Sum('total')).values('sum')

        final = queryset.annotate(
            subscription_amount=Coalesce(ExpressionWrapper(
                Subquery(entries),
                output_field=DecimalField(decimal_places=2)
            ), Decimal('0.00')) + F('plan__amount')
        ).values(
            'subscription_amount', 'id', 'plan', 'plan__name', 'customer__first_name',
            'customer__last_name'
        ).order_by('-subscription_amount')

        tupleList = []
        for i in final:
            if not tupleList:
                data = {'granulations': {
                    'plan': {
                        'name': i['plan__name'],
                        'id': i['plan']
                    }},
                    'values': [
                        {
                            'subscription_id': i['id'],
                            'estimated_income': i['subscription_amount'],
                            'customer_name': i['customer__first_name'] + i['customer__last_name']
                        }
                    ]
                }
                tupleList.append(data)
            else:
                ok = 0
                for item in tupleList:
                    for key, value in item.iteritems():
                        if key == 'granulations':
                            for keys, values in value.iteritems():
                                if values['name'] == i['plan__name']:
                                    item['values'].append(
                                        {
                                            'subscription_id': i['id'],
                                            'estimated_income': i['subscription_amount'],
                                            'customer_name': i['customer__first_name'] + i['customer__last_name']
                                        }
                                    )
                                    ok = 1
                if ok == 0:
                    data = {
                        'granulations': {
                            'plan': {
                                'name': i['plan__name'],
                                'id': i['plan']
                            }},
                        'values': [
                            {
                                'subscription_id': i['id'],
                                'estimated_income': i['subscription_amount'],
                                'customer_name': i['customer__first_name'] + i[
                                    'customer__last_name']
                            }
                        ]
                    }
                    tupleList.append(data)

        if self.modifier is not None:
            for i in Plan.objects.exclude(subscription__isnull=False).distinct():
                data = {'granulations': {
                    'plan': {
                        'name': i.name,
                        'url': 'someUrl'
                    }},
                    'values': []
                }
                tupleList.append(data)

        return tupleList

    def get_result(self):
        if self.queryset.model == Transaction:
            if self.modifier is not None:
                method_name = 'transactions_' + self.result_type + '_' + self.modifier
                method = getattr(self, method_name)
                return method(self.queryset)
            else:
                method_name = 'transactions_' + self.result_type
                method = getattr(self, method_name)
                return method(self.queryset)
        elif self.queryset.model == Invoice or self.queryset.model == Proforma:
            if self.modifier is not None:
                method_name = 'documents_' + self.result_type + '_' + self.modifier
                method = getattr(self, method_name)
                return method(self.queryset)
            else:
                method_name = 'documents_' + self.result_type
                method = getattr(self, method_name)
                return method(self.queryset)
        elif self.queryset.model == Subscription:
                method_name = 'subscriptions_' + self.result_type
                method = getattr(self, method_name)
                return method(self.queryset)
