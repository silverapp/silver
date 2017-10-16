from silver.models import Transaction, Invoice, Proforma, Subscription, Plan, BillingLog
from datetime import datetime

from collections import namedtuple


class Stats(object):

    result_types = {
        'transactions': {
            'amount': {
                'modifiers': [],
                'granulations': {
                    'created_at': ['year', 'month', 'day'],
                    'currency': [],
                    'customer': []
                }
            }
        },
        'documents': {
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
        'billing_log': {
            'total': {
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

    def get_granulations(self):
        granulation_arguments = {}
        for granulation in self.granulations:
            name = granulation['name']
            if ((self.queryset.model == Transaction and name in ['created_at', 'updated_at']) or
                    (self.queryset.model == Invoice and name in ['issue_date', 'paid_date']) or
                    (self.queryset.model == BillingLog and name == 'plan')):
                granulation_arguments['granulation_field'] = name
                if granulation['value'] is not None:
                    granulation_arguments['time_granulation_interval'] = granulation['value']
            else:
                granulation_arguments['additional_granulation_field'] = name
        return granulation_arguments

    def documents_overdue_payments(self, queryset):
        stats_list = []
        for i in queryset.filter(due_date__lte=datetime.now(), state=Invoice.STATES.ISSUED):
            name = i.customer.first_name + " " + i.customer.last_name
            new_document = {'customer': name,
                            'due_date': i.due_date,
                            'values': []
                            }
            data = {
                'total': i.total,
                'paid': i.amount_paid_in_transaction_currency,
                'left': i.amount_to_be_charged_in_transaction_currency
            }
            new_document['values'] = data

            stats_list.append(new_document)

        return stats_list

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

    def _get_time_granulations(self, document, granulation_arguments, granulation_field):
        if 'time_granulation_interval' in granulation_arguments \
                and 'time_granulation_interval' is not None:
            if granulation_arguments['time_granulation_interval'] == 'year':
                return str(getattr(document, granulation_field).year)
            elif granulation_arguments['time_granulation_interval'] == 'month':
                month = self._numbers_to_strings(getattr(document, granulation_field).month)
                return str(getattr(document, granulation_field).year) + ' ' + month
            elif granulation_arguments['time_granulation_interval'] == 'day':
                day = self._numbers_to_strings(
                    getattr(document, granulation_field).month) + ' ' + str(
                    getattr(document, granulation_field).day)
                return str(getattr(document, granulation_field).year) + ' ' + day

    def _add_item_to_list(self, item, doc, granulation_arguments, customer_name, amount, id,
                          additional_field):
        search_document = doc.get(item, [])

        details = {'id': id}
        if amount is not None:
            details['total'] = amount
        if 'additional_granulation_field' not in granulation_arguments:
            details['customer_name'] = customer_name
        if additional_field is not None:
            details[next(iter(additional_field))] = additional_field[next(iter(additional_field))]

        doc[item] = search_document + [details]

    def _name_tuple(self, granulation_arguments):
        if 'granulation_field' in granulation_arguments:
            if 'additional_granulation_field' in granulation_arguments:
                return namedtuple("group_by", ["name", "granulation", "currency"])
            else:
                return namedtuple("group_by", ["granulation", "currency"])
        elif 'additional_granulation_field' in granulation_arguments:
            return namedtuple("group_by", ["name", "currency"])
        else:
            return namedtuple("group_by", ["currency"])

    def get_stats_data(self, granulation_arguments, customer_name, currency, amount,
                       granulation_value, id, doc, additional_field):
        name_tuple = self._name_tuple(granulation_arguments)
        if 'granulation_field' in granulation_arguments:
            if 'additional_granulation_field' in granulation_arguments:
                item = name_tuple(granulation=granulation_value, name=customer_name,
                                  currency=currency)
                self._add_item_to_list(item, doc, granulation_arguments, customer_name, amount, id,
                                       additional_field)
            else:
                item = name_tuple(granulation=granulation_value, currency=currency)
                self._add_item_to_list(item, doc, granulation_arguments, customer_name, amount, id,
                                       additional_field)

        elif 'additional_granulation_field' in granulation_arguments:
            item = name_tuple(name=customer_name, currency=currency)
            self._add_item_to_list(item, doc, granulation_arguments, customer_name, amount, id,
                                   additional_field)

    def _serialize_result(self, doc, stats_list, granulation_field, granulation_arguments):
        for key in sorted(doc.keys()):
            data = dict()
            data['currency'] = key.currency
            if 'additional_granulation_field' in granulation_arguments:
                data['customer_name'] = key.name
            if 'granulation_field' in granulation_arguments:
                data[granulation_field] = key.granulation
            data['values'] = []
            for subscription in sorted(doc[key]):
                data['values'].append(subscription)
            stats_list.append(data)

    def documents_amount(self, queryset):
        stats_list = []
        doc = dict()
        granulation_arguments = self.get_granulations()

        if 'granulation_field' in granulation_arguments:
            granulation_field = granulation_arguments['granulation_field']
        else:
            granulation_field = None

        if granulation_field is not None:
            filter_field = {granulation_field + '__isnull': True}
        else:
            filter_field = {'issue_date' + '__isnull': True}

        for document in queryset.exclude(**filter_field):
            customer_name = document.customer.first_name + " " + document.customer.last_name
            if 'time_granulation_interval' in granulation_arguments:
                granulation_value = self._get_time_granulations(document, granulation_arguments,
                                                                granulation_field)
            else:
                granulation_value = None

            self.get_stats_data(granulation_arguments, customer_name, document.currency,
                                document.total, granulation_value, document.id, doc, None)

        self._serialize_result(doc, stats_list, granulation_field, granulation_arguments)

        return stats_list

    def documents_paid_date(self, queryset):
        stats_list = []
        doc = dict()
        granulation_arguments = self.get_granulations()

        if 'granulation_field' in granulation_arguments:
            granulation_field = granulation_arguments['granulation_field']
        else:
            granulation_field = None

        for document in queryset.exclude(paid_date__isnull=True):
            customer_name = document.customer.first_name + " " + document.customer.last_name
            if 'time_granulation_interval' in granulation_arguments:
                granulation_value = self._get_time_granulations(document, granulation_arguments,
                                                                granulation_field)
            else:
                granulation_value = None

            self.get_stats_data(granulation_arguments, customer_name, document.currency, None,
                                granulation_value, document.id, doc, None)

        self._serialize_result(doc, stats_list, granulation_field, granulation_arguments)

        return stats_list

    def billing_log_total(self, queryset):
        stats_list = []
        doc = dict()
        granulation_arguments = self.get_granulations()

        if 'granulation_field' in granulation_arguments:
            granulation_field = granulation_arguments['granulation_field']
        else:
            granulation_field = None

        for document in queryset:
            customer_name = document.subscription.customer.first_name + " " + \
                            document.subscription.customer.last_name

            if 'granulation_field' in granulation_arguments:
                granulation_value = document.subscription.plan.name
            else:
                granulation_value = None

            additional_field = {"billing_date": document.billing_date}

            self.get_stats_data(granulation_arguments, customer_name,
                                document.subscription.plan.currency, document.total,
                                granulation_value, document.subscription.id, doc, additional_field)

        self._serialize_result(doc, stats_list, granulation_field, granulation_arguments)

        return stats_list

    def billing_log_total_include_unused_plans(self, queryset):
        stats_list = self.billing_log_total(queryset)
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

    def transactions_amount(self, queryset):
        stats_list = []
        doc = dict()
        granulation_arguments = self.get_granulations()

        if 'granulation_field' in granulation_arguments:
            granulation_field = granulation_arguments['granulation_field']
        else:
            granulation_field = None

        if granulation_field is not None:
            filter_field = {granulation_field + '__isnull': True}
        else:
            filter_field = {'created_at' + '__isnull': True}

        queryset = queryset.exclude(**filter_field)
        for document in queryset:
            customer_name = document.invoice.customer.first_name + " " + \
                            document.invoice.customer.last_name
            if 'time_granulation_interval' in granulation_arguments:
                granulation_value = self._get_time_granulations(document, granulation_arguments,
                                                                granulation_field)
            else:
                granulation_value = None

            self.get_stats_data(granulation_arguments, customer_name, document.currency,
                                document.amount, granulation_value, document.id, doc, None)

        self._serialize_result(doc, stats_list, granulation_field, granulation_arguments)

        return stats_list

    def _get_model_name(self):
        if self.queryset.model == Transaction:
            return 'transactions'
        elif self.queryset.model == Invoice or self.queryset.model == Proforma:
            return 'documents'
        elif self.queryset.model == BillingLog:
            return 'billing_log'

    def get_result(self):
        if self.modifier is not None:
            method_name = self._get_model_name() + '_' + self.result_type + '_' + self.modifier
            method = getattr(self, method_name)
            return method(self.queryset)
        else:
            method_name = self._get_model_name() + '_' + self.result_type
            method = getattr(self, method_name)
            return method(self.queryset)
