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

    def _validate_granulation_parameters(self, granulation_field, granulation_parameters,
                                         granulations):
        for granulation in self.granulations:

            # if the granulation field selected is incorrect
            if granulation['name'] not in granulations:
                raise ValueError("The granulation field is incorrect")

            # if the granulation field from the result_types dictionary corresponds with the
            # granulation field selected by the user
            if granulation_field == granulation['name']:

                # if the granulation field doesn't have granulation parameters
                if not granulation_parameters:
                    # but the user selected one
                    if granulation['value'] != 'True':
                        raise ValueError("The granulation doesn't have parameters: "
                                         "Try granulation_field=True")
                    # go to the next granulation field selected
                    continue

                # if the granulation field has granulation parameters but the ones introduced are
                # not correct
                if granulation_parameters and granulation['value'] not in granulation_parameters:
                    raise ValueError("The granulation parameter is incorrect: "
                                     "Try granulation_field=month")

    def validate(self):
        if self.queryset.model != Transaction and self.queryset.model != Invoice \
                and self.queryset.model != Subscription and self.queryset.model != BillingLog:
            raise ValueError('Invalid model, choices are: Transaction, Invoice, BillingLog')
        if self.result_type is None:
            raise ValueError('Select a result type: choices are: amount, overdue_payments, '
                             'paid_date, total')

        for model, metrics in self.result_types.iteritems():
            # iterate the result_types dictionary to validate the selected granulations
            # and modifiers

            if model != self._get_model_name():
                continue

            # if the selected model doesn't have the selected result_type
            if self.result_type not in metrics:
                raise ValueError('Invalid result type, choices are: amount, overdue_payments, '
                                 'paid_date, total')

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
                    self._validate_granulation_parameters(granulation_field, granulation_parameters,
                                                          values['granulations'])

        return True

    # iterates the granulated_stats dictionary and creates the stats_list
    def _create_stats_list(self, granulated_stats, stats_list, granulation_field,
                           granulation_arguments):
        for key in sorted(granulated_stats.keys()):
            data = dict()
            data['currency'] = key.currency
            if 'additional_granulation_field' in granulation_arguments:
                data['customer_name'] = key.name
            if 'granulation_field' in granulation_arguments:
                data[granulation_field] = key.granulation
            data['values'] = []
            for subscription in sorted(granulated_stats[key]):
                data['values'].append(subscription)
            stats_list.append(data)

    # search the elements that correspond with the granulation tuple key given
    def _search_element(self, tuple_key, granulated_stats, granulation_arguments, customer_name,
                        amount, id, additional_field):

        search_tuple_key = granulated_stats.get(tuple_key, [])

        details = {'id': id}
        if amount is not None:
            details['total'] = amount
        if 'additional_granulation_field' not in granulation_arguments:
            details['customer_name'] = customer_name
        if additional_field is not None:
            details[additional_field.items()[0][0]] = additional_field.items()[0][1]

        granulated_stats[tuple_key] = search_tuple_key + [details]

    # names the keys in the granulation tuple thus providing a way to access them
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

    # gets a tuple formed by the selected granulations
    def get_granulation_tuple(self, granulation_arguments, customer_name, currency, amount,
                              granulation_value, id, granulated_stats, additional_field):

        name_tuple = self._name_tuple(granulation_arguments)

        if 'granulation_field' in granulation_arguments:
            if 'additional_granulation_field' in granulation_arguments:
                tuple_key = name_tuple(granulation=granulation_value, name=customer_name,
                                       currency=currency)
                self._search_element(tuple_key, granulated_stats, granulation_arguments,
                                     customer_name, amount, id, additional_field)
            else:
                tuple_key = name_tuple(granulation=granulation_value, currency=currency)
                self._search_element(tuple_key, granulated_stats, granulation_arguments,
                                     customer_name, amount, id, additional_field)

        elif 'additional_granulation_field' in granulation_arguments:
            tuple_key = name_tuple(name=customer_name, currency=currency)
            self._search_element(tuple_key, granulated_stats, granulation_arguments, customer_name,
                                 amount, id, additional_field)

    # returns the formatted granulation date according to the selected granulation parameter
    def _get_time_granulations(self, document, granulation_arguments, granulation_field):
        if 'time_granulation_interval' in granulation_arguments \
                and 'time_granulation_interval' is not None:
            if granulation_arguments['time_granulation_interval'] == 'year':
                return getattr(document, granulation_field).strftime('%Y')
            elif granulation_arguments['time_granulation_interval'] == 'month':
                return getattr(document, granulation_field).strftime('%b %Y')
            elif granulation_arguments['time_granulation_interval'] == 'day':
                return getattr(document, granulation_field).strftime('%d %b %Y')

    # creates the granulation_arguments list that contains the granulations selected by the user
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

    def documents_amount(self, queryset):
        stats_list = []
        granulated_stats = dict()
        granulation_arguments = self.get_granulations()

        if 'granulation_field' in granulation_arguments:
            granulation_field = granulation_arguments['granulation_field']
        else:
            granulation_field = None

        if granulation_field is not None:
            filter_field = {granulation_field + '__isnull': True}
            queryset = queryset.exclude(**filter_field)

        for document in queryset:
            customer_name = document.customer.first_name + " " + document.customer.last_name
            if 'time_granulation_interval' in granulation_arguments:
                granulation_value = self._get_time_granulations(document, granulation_arguments,
                                                                granulation_field)
            else:
                granulation_value = None

            self.get_granulation_tuple(granulation_arguments, customer_name, document.currency,
                                       document.total, granulation_value, document.id,
                                       granulated_stats, additional_field=None)

        self._create_stats_list(granulated_stats, stats_list, granulation_field,
                                granulation_arguments)

        return stats_list

    def documents_payment_day(self, queryset):
        stats_list = []
        granulated_stats = dict()
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

            additional_field = {"payment_day": document.paid_date.strftime('%d')}

            self.get_granulation_tuple(granulation_arguments, customer_name, document.currency,
                                       None, granulation_value, document.id, granulated_stats,
                                       additional_field)

        self._create_stats_list(granulated_stats, stats_list, granulation_field,
                                granulation_arguments)

        return stats_list

    def billing_log_total(self, queryset):
        stats_list = []
        granulated_stats = dict()
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

            additional_field = {"billing_date": document.billing_date.strftime('%m/%d/%Y')}

            self.get_granulation_tuple(granulation_arguments, customer_name,
                                       document.subscription.plan.currency, document.total,
                                       granulation_value, document.subscription.id,
                                       granulated_stats, additional_field)

        self._create_stats_list(granulated_stats, stats_list, granulation_field,
                                granulation_arguments)

        return stats_list

    def billing_log_total_include_unused_plans(self, queryset):
        stats_list = self.billing_log_total(queryset)
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
        stats_list = []
        granulated_stats = dict()
        granulation_arguments = self.get_granulations()

        if 'granulation_field' in granulation_arguments:
            granulation_field = granulation_arguments['granulation_field']
        else:
            granulation_field = None

        for document in queryset:
            customer_name = document.invoice.customer.first_name + " " + \
                            document.invoice.customer.last_name
            if 'time_granulation_interval' in granulation_arguments:
                granulation_value = self._get_time_granulations(document, granulation_arguments,
                                                                granulation_field)
            else:
                granulation_value = None

            self.get_granulation_tuple(granulation_arguments, customer_name, document.currency,
                                       document.amount, granulation_value, document.id,
                                       granulated_stats, None)

        self._create_stats_list(granulated_stats, stats_list, granulation_field,
                                granulation_arguments)

        return stats_list

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

    def _get_model_name(self):
        if self.queryset.model == Transaction:
            return 'transactions'
        elif self.queryset.model == Invoice or self.queryset.model == Proforma:
            return 'documents'
        elif self.queryset.model == BillingLog:
            return 'billing_log'

    def get_result(self):
        isValid = self.validate()
        if isValid is True:
            if self.modifier is not None:
                method_name = self._get_model_name() + '_' + self.result_type + '_' + self.modifier
                method = getattr(self, method_name)
                return method(self.queryset)
            else:
                method_name = self._get_model_name() + '_' + self.result_type
                method = getattr(self, method_name)
                return method(self.queryset)
        else:
            return isValid
