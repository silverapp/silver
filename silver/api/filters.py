# Copyright (c) 2015 Presslabs SRL
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from django_filters import (FilterSet, CharFilter, BooleanFilter, DateFilter,
                            NumberFilter)
from django_filters.fields import Lookup

from silver.models import (MeteredFeature, Subscription, Customer, Provider,
                           Plan, Invoice, Proforma, Transaction, PaymentMethod,
                           BillingDocumentBase)


class MultipleCharFilter(CharFilter):
    def filter(self, qs, value):
        if value:
            value = value.split(',')

        lookup = Lookup(value, 'in')
        return super(MultipleCharFilter, self).filter(qs, lookup)


class MeteredFeaturesFilter(FilterSet):
    name = CharFilter(name='name', lookup_expr='icontains')

    class Meta:
        model = MeteredFeature
        fields = ('name', )


class SubscriptionFilter(FilterSet):
    plan = CharFilter(name='plan__name', lookup_expr='iexact')
    reference = MultipleCharFilter(name='reference', lookup_expr='iexact')

    class Meta:
        model = Subscription
        fields = ['plan', 'reference', 'state']


class CustomerFilter(FilterSet):
    active = BooleanFilter(name='is_active', lookup_expr='iexact')
    email = CharFilter(name='email', lookup_expr='icontains')
    company = CharFilter(name='company', lookup_expr='icontains')
    first_name = CharFilter(name='first_name', lookup_expr='icontains')
    last_name = CharFilter(name='last_name', lookup_expr='icontains')
    country = CharFilter(name='country', lookup_expr='icontains')
    sales_tax_name = CharFilter(name='sales_tax_name', lookup_expr='icontains')
    sales_tax_number = CharFilter(name='sales_tax_number',
                                  lookup_expr='icontains')
    consolidated_billing = CharFilter(name='consolidated_billing',
                                      lookup_expr='icontains')
    reference = MultipleCharFilter(name='customer_reference',
                                   lookup_expr='iexact')

    class Meta:
        model = Customer
        fields = ['email', 'first_name', 'last_name', 'company', 'active',
                  'country', 'reference', 'sales_tax_name',
                  'consolidated_billing', 'sales_tax_number']


class ProviderFilter(FilterSet):
    email = CharFilter(name='email', lookup_expr='icontains')
    company = CharFilter(name='company', lookup_expr='icontains')

    class Meta:
        model = Provider
        fields = ['email', 'company']


class PlanFilter(FilterSet):
    name = CharFilter(name='name', lookup_expr='icontains')
    currency = CharFilter(name='currency', lookup_expr='icontains')
    enabled = BooleanFilter(name='enabled', lookup_expr='iexact')
    private = BooleanFilter(name='private', lookup_expr='iexact')
    interval = CharFilter(name='interval', lookup_expr='icontains')
    product_code = CharFilter(name='product_code', lookup_expr='icontains')
    provider = CharFilter(name='provider__company', lookup_expr='icontains')

    class Meta:
        model = Plan
        fields = ['name', 'currency', 'enabled', 'private', 'product_code',
                  'provider', 'interval']


class BillingDocumentFilter(FilterSet):
    id = NumberFilter(name='id', lookup_expr='iexact')
    state = MultipleCharFilter(name='state', lookup_expr='iexact')
    number = NumberFilter(name='number', lookup_expr='iexact')
    customer = NumberFilter(name='customer__pk', lookup_expr='iexact')
    customer_name = CharFilter(name='customer__name', lookup_expr='icontains')
    customer_company = CharFilter(name='customer__company',
                                  lookup_expr='icontains')
    provider_name = CharFilter(name='provider__name', lookup_expr='icontains')
    provider_company = CharFilter(name='provider__company',
                                  lookup_expr='icontains')
    issue_date = DateFilter(name='issue_date', lookup_expr='iexact')
    due_date = DateFilter(name='due_date', lookup_expr='iexact')
    paid_date = DateFilter(name='due_date', lookup_expr='iexact')
    cancel_date = DateFilter(name='cancel_date', lookup_expr='iexact')
    currency = MultipleCharFilter(name='currency', lookup_expr='icontains')
    sales_tax_name = MultipleCharFilter(name='sales_tax_name', lookup_expr='icontains')
    is_overdue = BooleanFilter(name='overdue', method='filter_is_overdue')

    def filter_is_overdue(self, queryset, _, value):
        if value:
            return queryset.overdue()
        return queryset.not_overdue()

    class Meta:
        model = BillingDocumentBase
        fields = ['id', 'state', 'number', 'customer_name', 'customer_company',
                  'provider_name', 'provider_company', 'issue_date', 'due_date',
                  'paid_date', 'cancel_date', 'currency', 'sales_tax_name',
                  'is_overdue']


class InvoiceFilter(BillingDocumentFilter):
    series = CharFilter(name='provider__invoice_series',
                        lookup_expr='icontains')

    class Meta(BillingDocumentFilter.Meta):
        model = Invoice
        fields = BillingDocumentFilter.Meta.fields + ['series', ]


class ProformaFilter(BillingDocumentFilter):
    series = CharFilter(name='provider__proforma_series',
                        lookup_expr='icontains')

    class Meta(BillingDocumentFilter.Meta):
        model = Proforma
        fields = BillingDocumentFilter.Meta.fields + ['series', ]


class TransactionFilter(FilterSet):
    payment_processor = CharFilter(
        name='payment_method__payment_processor',
        lookup_expr='iexact'
    )
    state = CharFilter(name='state')
    min_amount = NumberFilter(name='amount', lookup_expr='gte')
    max_amount = NumberFilter(name='amount', lookup_expr='lte')
    currency = CharFilter(name='currency', lookup_expr='iexact')
    disabled = BooleanFilter(name='disabled')

    class Meta:
        model = Transaction
        fields = ['payment_method', 'state', 'min_amount', 'max_amount',
                  'currency', 'disabled']


class PaymentMethodFilter(FilterSet):
    processor = CharFilter(name='payment_processor', lookup_expr='iexact')
    canceled = BooleanFilter(name='canceled')
    verified = BooleanFilter(name='verified')

    class Meta:
        model = PaymentMethod
        fields = ['processor', 'canceled', 'verified']
