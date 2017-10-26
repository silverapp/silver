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
            'payment_day': {
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
        'billing_logs': {
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
        self.granulations = granulations

    def validate(self):
        if self.queryset.model != Transaction and self.queryset.model != Invoice \
                and self.queryset.model != BillingLog:
            raise ValueError('Invalid model')
        if self.result_type is None:
            raise ValueError('A result type is required')

        for model, metrics in self.result_types.iteritems():
            # iterate the result_types dictionary to validate the selected granulations
            # and modifiers

            if model != self._get_model_name():
                continue

            # if the selected model doesn't have the selected result_type
            if self.result_type not in metrics:
                raise ValueError('Invalid result type')

            # search for the selected result_type in the selected model's keys
            for result_type, values in metrics.iteritems():
                if result_type != self.result_type:
                    continue
                else:

                    # if the result_type doesn't have modifiers
                    if not values['modifiers']:
                        if self.modifier is not None:
                            raise ValueError("The result type doesn't have modifiers")

                    # if a modifier has to be selected
                    elif None not in values['modifiers'] and self.modifier is None:
                        raise ValueError('The modifier argument is required.')

                    # if the selected modifier is incorrect
                    elif self.modifier not in values['modifiers']:
                        raise ValueError('Invalid modifier')

                # foreach granulation field verify if it has granulation parameters or if they
                # are correct
                for granulation_field, granulation_parameters in values['granulations'].iteritems():
                    if 'granulation_field' in self.granulations:
                        # iterate until you find in the result_types dict the corresponding
                        # granulation field
                        if granulation_field != self.granulations['granulation_field']:
                            continue
                        else:
                            if 'time granulation_interval' in self.granulations \
                                    and self.granulations['time_granulation_interval'] not in \
                                    granulation_parameters:
                                raise ValueError('Invalid granulation parameter')

        return True

    # iterates the granulated_stats dictionary and creates the stats_list
    def _create_stats_list(self, granulated_stats, granulation_field):
        stats_list = []
        for key in sorted(granulated_stats.keys()):
            data = dict()
            data['currency'] = key.currency
            if 'additional_granulation_field' in self.granulations:
                data['customer_name'] = key.name
            if 'granulation_field' in self.granulations:
                data[granulation_field] = key.granulation
            data['values'] = []
            for subscription in sorted(granulated_stats[key]):
                data['values'].append(subscription)
            stats_list.append(data)

        return stats_list

    # searches the elements that correspond with the granulation tuple key given and appends a new
    # element in case it finds one
    def _append_element_to_key(self, tuple_key, granulated_stats, stats_details):
        # tuple_key = ('issue_date':Mar 2017, 'currency': 'USD')
        # search_key = [{"id": 1, "total": 200}, {"id": 2, "total": 199}]
        # stats_data = {"id": 3, "total": 25}

        search_key = granulated_stats.get(tuple_key, [])
        granulated_stats[tuple_key] = search_key + [stats_details]

    # names the keys in the granulation tuple thus providing a way to access them
    def _name_tuple(self):
        if 'granulation_field' in self.granulations:
            if 'additional_granulation_field' in self.granulations:
                return namedtuple("group_by", ["name", "granulation", "currency"])
            else:
                return namedtuple("group_by", ["granulation", "currency"])
        elif 'additional_granulation_field' in self.granulations:
            return namedtuple("group_by", ["name", "currency"])
        else:
            return namedtuple("group_by", ["currency"])

    # gets a tuple key formed by the selected granulations
    def get_granulation_key(self, customer_name, currency, granulation_value,
                            granulated_stats, stats_details):

        name_tuple = self._name_tuple()

        if 'granulation_field' in self.granulations:
            if 'additional_granulation_field' in self.granulations:
                tuple_key = name_tuple(granulation=granulation_value, name=customer_name,
                                       currency=currency)
                self._append_element_to_key(tuple_key, granulated_stats, stats_details)
            else:
                tuple_key = name_tuple(granulation=granulation_value, currency=currency)
                self._append_element_to_key(tuple_key, granulated_stats, stats_details)

        elif 'additional_granulation_field' in self.granulations:
            tuple_key = name_tuple(name=customer_name, currency=currency)
            self._append_element_to_key(tuple_key, granulated_stats, stats_details)
        else:
            tuple_key = name_tuple(currency=currency)
            self._append_element_to_key(tuple_key, granulated_stats, stats_details)

    # returns the formatted granulation date according to the selected granulation parameter
    def _get_time_granulations(self, document, granulation_field):
        if 'time_granulation_interval' in self.granulations \
                and 'time_granulation_interval' is not None:
            if self.granulations['time_granulation_interval'] == 'year':
                return getattr(document, granulation_field).strftime('%s')
            elif self.granulations['time_granulation_interval'] == 'month':
                return getattr(document, granulation_field).strftime('%s')
            elif self.granulations['time_granulation_interval'] == 'day':
                return getattr(document, granulation_field).strftime('%s')

    def documents_amount(self, queryset):
        granulated_stats = dict()

        if 'granulation_field' in self.granulations:
            granulation_field = self.granulations['granulation_field']
        else:
            granulation_field = None

        if granulation_field is not None:
            filter_field = {granulation_field + '__isnull': True}
            queryset = queryset.exclude(**filter_field)

        for document in queryset:
            customer_name = document.customer.first_name + " " + document.customer.last_name
            if 'time_granulation_interval' in self.granulations:
                granulation_value = self._get_time_granulations(document, granulation_field)
            else:
                granulation_value = None

            stats_details = {
                "total": document.total,
                "id": document.id
            }

            if 'additional_granulation_field' not in self.granulations:
                stats_details['customer'] = customer_name

            self.get_granulation_key(customer_name, document.currency, granulation_value,
                                     granulated_stats, stats_details)

        return self._create_stats_list(granulated_stats, granulation_field)

    def documents_payment_day(self, queryset):
        granulated_stats = dict()

        if 'granulation_field' in self.granulations:
            granulation_field = self.granulations['granulation_field']
        else:
            granulation_field = None

        for document in queryset.exclude(paid_date__isnull=True):
            customer_name = document.customer.first_name + " " + document.customer.last_name
            if 'time_granulation_interval' in self.granulations:
                granulation_value = self._get_time_granulations(document, granulation_field)
            else:
                granulation_value = None

            stats_details = {
                "id": document.id,
                "payment_day": document.paid_date.strftime('%d')
            }

            if 'additional_granulation_field' not in self.granulations:
                stats_details['customer'] = customer_name

            self.get_granulation_key(customer_name, document.currency, granulation_value,
                                     granulated_stats, stats_details)

        return self._create_stats_list(granulated_stats, granulation_field)

    def billing_logs_total(self, queryset):
        granulated_stats = dict()

        if 'granulation_field' in self.granulations:
            granulation_field = self.granulations['granulation_field']
        else:
            granulation_field = None

        for billing_log in queryset:
            customer_name = billing_log.subscription.customer.first_name + " " + \
                            billing_log.subscription.customer.last_name

            if 'granulation_field' in self.granulations:
                granulation_value = billing_log.subscription.plan.name
            else:
                granulation_value = None

            stats_details = {
                "id": billing_log.subscription.id,
                "total": billing_log.total,
                "billing_date": billing_log.billing_date.isoformat()
            }
            if 'additional_granulation_field' not in self.granulations:
                stats_details['customer'] = customer_name

            self.get_granulation_key(customer_name, billing_log.subscription.plan.currency,
                                     granulation_value, granulated_stats, stats_details)

        return self._create_stats_list(granulated_stats, granulation_field)

    def billing_logs_total_include_unused_plans(self, queryset):
        stats_list = self.billing_logs_total(queryset)
        for plan in Plan.objects.exclude(subscription__isnull=False).distinct():
            data = {'granulations': {
                'plan': {
                    'name': plan.name,
                    'id': plan.id
                }},
                'values': []
            }
            stats_list.append(data)
        return stats_list

    def transactions_amount(self, queryset):
        granulated_stats = dict()

        if 'granulation_field' in self.granulations:
            granulation_field = self.granulations['granulation_field']
        else:
            granulation_field = None

        for transaction in queryset:
            customer_name = transaction.invoice.customer.first_name + " " + \
                            transaction.invoice.customer.last_name
            if 'time_granulation_interval' in self.granulations:
                granulation_value = self._get_time_granulations(transaction,
                                                                granulation_field)
            else:
                granulation_value = None

            stats_details = {
                "id": transaction.id,
                "total": transaction.amount,
            }
            if 'additional_granulation_field' not in self.granulations:
                stats_details['customer'] = customer_name

            self.get_granulation_key(customer_name, transaction.currency, granulation_value,
                                     granulated_stats, stats_details)

        return self._create_stats_list(granulated_stats, granulation_field)

    def documents_overdue_payments(self, queryset):
        stats_list = []
        for document in queryset.filter(due_date__lte=datetime.now(), state=Invoice.STATES.ISSUED):
            name = document.customer.first_name + " " + document.customer.last_name
            new_document = {'customer': name,
                            'due_date': document.due_date,
                            'values': []
                            }
            data = {
                'total': document.total,
                'paid': document.amount_paid_in_transaction_currency,
                'left': document.amount_to_be_charged_in_transaction_currency
            }
            new_document['values'] = data

            stats_list.append(new_document)

        return stats_list

    def _get_model_name(self):
        if self.queryset.model == Transaction:
            return 'transactions'
        elif self.queryset.model == Invoice or self.queryset.model == Proforma:
            return 'documents'
        elif self.queryset.model == BillingLog:
            return 'billing_logs'

    def get_result(self):
        is_valid = self.validate()
        if is_valid is True:
            if self.modifier is not None:
                method_name = self._get_model_name() + '_' + self.result_type + '_' + self.modifier
                method = getattr(self, method_name)
                return method(self.queryset)
            else:
                method_name = self._get_model_name() + '_' + self.result_type
                method = getattr(self, method_name)
                return method(self.queryset)
        else:
            return is_valid
