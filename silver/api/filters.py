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

from __future__ import absolute_import

try:
    from django_filters import BaseInFilter
    _df_version = 2
except ImportError:
    from django_filters.fields import Lookup
    _df_version = 1.1


from django_filters import FilterSet, CharFilter, BooleanFilter, DateFilter, NumberFilter

from silver.models import (MeteredFeature, Subscription, Customer, Provider,
                           Plan, Invoice, Proforma, Transaction, PaymentMethod,
                           BillingDocumentBase)

if _df_version >= 2:
    class MultipleCharFilter(BaseInFilter, CharFilter):
        pass
else:
    # TODO remove this when Python2 is deprecated and django filters version must be >= 2
    class MultipleCharFilter(CharFilter):
        def filter(self, qs, value):
            if value:
                value = value.split(',')

            lookup = Lookup(value, 'in')
            return super(MultipleCharFilter, self).filter(qs, lookup)


class MeteredFeaturesFilter(FilterSet):
    name = CharFilter(field_name='name', lookup_expr='icontains')

    class Meta:
        model = MeteredFeature
        fields = ('name', )


class SubscriptionFilter(FilterSet):
    plan = CharFilter(field_name='plan__name', lookup_expr='iexact')
    reference = MultipleCharFilter(field_name='reference')

    class Meta:
        model = Subscription
        fields = ['plan', 'reference', 'state']


class CustomerFilter(FilterSet):
    active = BooleanFilter(field_name='is_active', lookup_expr='iexact')
    email = CharFilter(field_name='email', lookup_expr='icontains')
    company = CharFilter(field_name='company', lookup_expr='icontains')
    first_name = CharFilter(field_name='first_name', lookup_expr='icontains')
    last_name = CharFilter(field_name='last_name', lookup_expr='icontains')
    country = CharFilter(field_name='country', lookup_expr='icontains')
    sales_tax_name = CharFilter(field_name='sales_tax_name', lookup_expr='icontains')
    sales_tax_number = CharFilter(field_name='sales_tax_number',
                                  lookup_expr='icontains')
    consolidated_billing = CharFilter(field_name='consolidated_billing',
                                      lookup_expr='icontains')
    reference = MultipleCharFilter(field_name='customer_reference')

    class Meta:
        model = Customer
        fields = ['email', 'first_name', 'last_name', 'company', 'active',
                  'country', 'reference', 'sales_tax_name',
                  'consolidated_billing', 'sales_tax_number']


class ProviderFilter(FilterSet):
    email = CharFilter(field_name='email', lookup_expr='icontains')
    company = CharFilter(field_name='company', lookup_expr='icontains')

    class Meta:
        model = Provider
        fields = ['email', 'company']


class PlanFilter(FilterSet):
    name = CharFilter(field_name='name', lookup_expr='icontains')
    currency = CharFilter(field_name='currency', lookup_expr='icontains')
    enabled = BooleanFilter(field_name='enabled', lookup_expr='iexact')
    private = BooleanFilter(field_name='private', lookup_expr='iexact')
    interval = CharFilter(field_name='interval', lookup_expr='icontains')
    product_code = CharFilter(field_name='product_code', lookup_expr='icontains')
    provider = CharFilter(field_name='provider__company', lookup_expr='icontains')

    class Meta:
        model = Plan
        fields = ['name', 'currency', 'enabled', 'private', 'product_code',
                  'provider', 'interval']


class BillingDocumentFilter(FilterSet):
    id = NumberFilter(field_name='id', lookup_expr='iexact')
    state = MultipleCharFilter(field_name='state')
    number = NumberFilter(field_name='number', lookup_expr='iexact')
    customer = NumberFilter(field_name='customer__pk', lookup_expr='iexact')
    customer_name = CharFilter(field_name='customer__name', lookup_expr='icontains')
    customer_company = CharFilter(field_name='customer__company',
                                  lookup_expr='icontains')
    provider_name = CharFilter(field_name='provider__name', lookup_expr='icontains')
    provider_company = CharFilter(field_name='provider__company',
                                  lookup_expr='icontains')
    issue_date = DateFilter(field_name='issue_date', lookup_expr='iexact')
    due_date = DateFilter(field_name='due_date', lookup_expr='iexact')
    paid_date = DateFilter(field_name='due_date', lookup_expr='iexact')
    cancel_date = DateFilter(field_name='cancel_date', lookup_expr='iexact')
    currency = MultipleCharFilter(field_name='currency')
    sales_tax_name = MultipleCharFilter(field_name='sales_tax_name')
    is_overdue = BooleanFilter(field_name='overdue', method='filter_is_overdue')

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
    series = CharFilter(field_name='provider__invoice_series',
                        lookup_expr='icontains')

    class Meta(BillingDocumentFilter.Meta):
        model = Invoice
        fields = BillingDocumentFilter.Meta.fields + ['series', ]


class ProformaFilter(BillingDocumentFilter):
    series = CharFilter(field_name='provider__proforma_series',
                        lookup_expr='icontains')

    class Meta(BillingDocumentFilter.Meta):
        model = Proforma
        fields = BillingDocumentFilter.Meta.fields + ['series', ]


class TransactionFilter(FilterSet):
    payment_processor = CharFilter(
        field_name='payment_method__payment_processor',
        lookup_expr='iexact'
    )
    state = CharFilter(field_name='state')
    min_amount = NumberFilter(field_name='amount', lookup_expr='gte')
    max_amount = NumberFilter(field_name='amount', lookup_expr='lte')
    currency = CharFilter(field_name='currency', lookup_expr='iexact')
    disabled = BooleanFilter(field_name='disabled')

    class Meta:
        model = Transaction
        fields = ['payment_method', 'state', 'min_amount', 'max_amount',
                  'currency', 'disabled']


class PaymentMethodFilter(FilterSet):
    processor = CharFilter(field_name='payment_processor', lookup_expr='iexact')
    canceled = BooleanFilter(field_name='canceled')
    verified = BooleanFilter(field_name='verified')

    class Meta:
        model = PaymentMethod
        fields = ['processor', 'canceled', 'verified']
