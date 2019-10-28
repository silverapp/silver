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

from __future__ import absolute_import, unicode_literals

import errno
import logging
import os
from collections import OrderedDict, defaultdict
from datetime import date
from decimal import Decimal

import requests
from PyPDF2 import PdfFileReader, PdfFileMerger
from dal import autocomplete
from django_fsm import TransitionNotAllowed
from furl import furl

from django import forms
from django.contrib import messages
from django.contrib.admin import (
    helpers, site, TabularInline, ModelAdmin, SimpleListFilter
)
from django.contrib.admin.actions import delete_selected as delete_selected_
from django.contrib.admin.models import LogEntry, CHANGE
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models import BLANK_CHOICE_DASH, F, Value, fields
from django.db.models.functions import ExtractYear, ExtractMonth, Concat
from django.forms import ChoiceField
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_text
from django.utils.html import escape, conditional_escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from silver.documents_generator import DocumentsGenerator
from silver.models import (
    Plan, MeteredFeature, Subscription, Customer, Provider,
    MeteredFeatureUnitsLog, Invoice, DocumentEntry,
    ProductCode, Proforma, BillingLog, BillingDocumentBase,
    Transaction, PaymentMethod
)
from silver.payment_processors.mixins import PaymentProcessorTypes
from silver.utils.international import currencies
from silver.utils.payments import get_payment_url

logger = logging.getLogger('silver')


def metadata(obj):
    d = u'(None)'
    if obj.meta:
        d = u''
        for key, value in obj.meta.items():
            d += u'%s: <code>%s</code><br>' % (escape(key), escape(value))
    return d
metadata.allow_tags = True


def tax(obj):
    return ("{} {:.2f}%".format(obj.sales_tax_name, obj.sales_tax_percent)
            if obj.sales_tax_percent else '')
tax.admin_order_field = 'sales_tax_percent'


class LiveModelAdmin(ModelAdmin):
    def get_queryset(self, request):
        qs = self.model.all_objects.get_queryset()
        ordering = self.get_ordering(request)
        if ordering:
            qs = qs.order_by(*ordering)
        return qs

    def delete_model(self, request, obj):
        if 'hard_delete' in dir(obj):
            obj.hard_delete()
        else:
            super(LiveModelAdmin, self).delete_model(request, obj)

    def delete_selected(self, request, queryset):
        if 'hard_delete' in dir(queryset):
            queryset.delete = queryset.hard_delete
        return delete_selected_(self, request, queryset)

    delete_selected.short_description = _("Delete selected "
                                          "%(verbose_name_plural)s")

    actions = ['delete_selected']


class PlanForm(forms.ModelForm):
    class Meta:
        model = Plan
        fields = ('provider', 'name', 'product_code', 'interval',
                  'interval_count', 'amount', 'currency', 'trial_period_days',
                  'generate_documents_on_trial_end', 'separate_cycles_during_trial', 'prebill_plan',
                  'cycle_billing_duration', 'generate_after', 'metered_features', 'enabled',
                  'private')

    def clean(self):
        metered_features = self.cleaned_data.get('metered_features')
        Plan.validate_metered_features(metered_features)
        return self.cleaned_data


class PlanAdmin(ModelAdmin):
    list_display = ['name', 'get_provider', 'description', 'interval_display',
                    'trial_period_days', 'enabled', 'private']
    search_fields = ['name']
    list_filter = ['provider']
    form = PlanForm

    def interval_display(self, obj):
        return ('{:d} {}s'.format(obj.interval_count, obj.interval)
                if obj.interval_count != 1
                else '{:d} {}'.format(obj.interval_count, obj.interval))

    interval_display.short_description = 'Interval'

    def description(self, obj):
        d = u'Subscription: <code>{:.2f} {}</code><br>'.format(obj.amount,
                                                               obj.currency)
        fmt = u'{name}: <code>{price:.2f} {currency}</code>'
        for f in obj.metered_features.all():
            d += fmt.format(
                name=f.name,
                price=f.price_per_unit,
                currency=obj.currency,
            )
            if f.included_units > 0:
                d += u'<code> ({:.2f} included)</code>'.format(f.included_units)
            d += u'<br>'
        return d

    description.allow_tags = True

    def get_provider(self, obj):
        return obj.provider.admin_change_url

    get_provider.allow_tags = True
    get_provider.short_description = "provider"
    get_provider.admin_order_field = "provider"

    def get_queryset(self, request):
        return super(PlanAdmin, self).get_queryset(request) \
            .prefetch_related("metered_features") \
            .select_related("provider")


class MeteredFeatureUnitsLogInLine(TabularInline):
    model = MeteredFeatureUnitsLog
    list_display = ['metered_feature']
    readonly_fields = ('start_date', 'end_date',)
    extra = 0

    def get_formset(self, request, obj=None, **kwargs):
        self.parent_obj = obj
        return super(MeteredFeatureUnitsLogInLine, self).get_formset(
            request, obj, **kwargs)

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'metered_feature' and hasattr(self, 'parent_obj'):
            if self.parent_obj:
                kwargs['queryset'] = db_field.rel.to.objects.filter(**{
                    'plan': self.parent_obj.plan
                })
        return super(MeteredFeatureUnitsLogInLine,
                     self).formfield_for_foreignkey(db_field, request,
                                                    **kwargs)


class BillingLogInLine(TabularInline):
    model = BillingLog
    fields = ['billing_date', 'plan_billed_up_to', 'metered_features_billed_up_to',
              'created_at', 'proforma_link', 'invoice_link']
    readonly_fields = fields
    verbose_name = 'Automatic billing log'
    verbose_name_plural = verbose_name

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def invoice_link(self, obj):
        return obj.invoice.admin_change_url if obj.invoice else 'None'

    invoice_link.short_description = 'Invoice'
    invoice_link.allow_tags = True

    def proforma_link(self, obj):
        return obj.proforma.admin_change_url if obj.proforma else 'None'

    proforma_link.short_description = 'Proforma'
    proforma_link.allow_tags = True


class SubscriptionForm(forms.ModelForm):
    class Meta:
        model = Subscription
        exclude = []
        readonly_fields = ['state', ]

        widgets = {
            'plan': autocomplete.ModelSelect2(
                url='autocomplete-plan'
            ),
            'customer': autocomplete.ModelSelect2(
                url='autocomplete-customer'
            ),
        }


class PlanFilter(SimpleListFilter):
    title = _('plan')
    parameter_name = 'plan'

    def lookups(self, request, model_admin):
        queryset = model_admin.get_queryset(request).distinct() \
            .annotate(
                _name_provider=Concat(
                    F('plan__name'), Value(' ('), F('plan__provider__name'), Value(')'),
                    output_field=fields.CharField()
                )
            ) \
            .values_list('id', '_name_provider') \
            .distinct()

        return list(queryset)

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(invoice__exact=self.value())
        return queryset


class SubscriptionAdmin(ModelAdmin):
    list_display = ['customer', 'get_plan_name', 'last_billing_date', 'trial_end',
                    'start_date', 'ended_at', 'state', metadata]
    list_filter = [PlanFilter, 'state', 'plan__provider', 'customer']
    actions = ['activate', 'cancel_now', 'cancel_at_end_of_cycle', 'end']
    search_fields = ['customer__first_name', 'customer__last_name',
                     'customer__company', 'plan__name', 'meta']
    readonly_fields = ['state']
    inlines = [MeteredFeatureUnitsLogInLine, BillingLogInLine]
    form = SubscriptionForm

    def get_queryset(self, request):
        return super(SubscriptionAdmin, self).get_queryset(request) \
                                             .prefetch_related('billing_logs') \
                                             .select_related('plan')

    def perform_action(self, request, action, queryset):
        try:
            method = getattr(Subscription, action)
        except AttributeError:
            self.message_user(request, 'Illegal action.', level=messages.ERROR)
            return

        failed_count = 0
        queryset_count = queryset.count()
        for entry in queryset:
            try:
                method(entry)
                entry.save()

                LogEntry.objects.log_action(
                    user_id=request.user.id,
                    content_type_id=ContentType.objects.get_for_model(entry).pk,
                    object_id=entry.id,
                    object_repr=force_text(entry),
                    action_flag=CHANGE,
                    change_message='{action} action initiated by user.'.format(
                        action=action.replace('_', ' ').strip().capitalize()
                    )
                )
            except TransitionNotAllowed:
                failed_count += 1
        if failed_count:
            if failed_count == queryset_count:
                self.message_user(request, 'Illegal state change attempt.',
                                  level=messages.ERROR)
            else:
                self.message_user(request, '%d state(s) changed (%d failed).' %
                                  (queryset_count - failed_count, failed_count),
                                  level=messages.WARNING)
        else:
            self.message_user(request, 'Successfully changed %d state(s).' %
                              queryset_count)

    def activate(self, request, queryset):
        self.perform_action(request, 'activate', queryset)

    activate.short_description = 'Activate the selected Subscription(s) '

    def reactivate(self, request, queryset):
        # NOTE: deactivated for now
        self.perform_action(request, 'reactivate', queryset)

    reactivate.short_description = 'Reactivate the selected Subscription(s) '

    def cancel_now(self, request, queryset):
        self.perform_action(request, '_cancel_now', queryset)

    cancel_now.short_description = 'Cancel the selected Subscription(s) now'

    def cancel_at_end_of_cycle(self, request, queryset):
        self.perform_action(request, '_cancel_at_end_of_billing_cycle', queryset)

    cancel_at_end_of_cycle.short_description = 'Cancel the ' \
                                               'selected Subscription(s) at the end ' \
                                               'of the billing cycle'

    def end(self, request, queryset):
        self.perform_action(request, 'end', queryset)

    end.short_description = 'End the selected Subscription(s) '

    def get_plan_name(self, subscription):
        return subscription.plan.name

    get_plan_name.short_description = "Plan"
    get_plan_name.admin_order_field = 'billing__plan__name'


class CustomerAdmin(LiveModelAdmin):
    fields = ['company', 'first_name', 'last_name', 'customer_reference',
              'email', 'phone', 'address_1', 'address_2', 'city', 'state',
              'zip_code', 'country', 'currency', 'consolidated_billing',
              'payment_due_days', 'sales_tax_name', 'sales_tax_percent',
              'sales_tax_number', 'extra', 'meta']
    list_display = ['name', 'customer_reference',
                    tax, 'consolidated_billing', metadata]
    search_fields = ['customer_reference', 'first_name', 'last_name', 'company',
                     'address_1', 'address_2', 'city', 'zip_code', 'country',
                     'state', 'email', 'meta']
    actions = ['generate_all_documents']
    exclude = ['live']

    def generate_all_documents(self, request, queryset):
        if request.POST.get('post'):
            billing_date = timezone.now().date()
            DocumentsGenerator().generate(billing_date=billing_date,
                                          customers=queryset,
                                          force_generate=True)

            msg = 'Successfully generated all user{term} documents.'
            if queryset.count() > 1:
                msg = msg.format(term='s\'')
            else:
                msg = msg.format(term='\'s')
            self.message_user(request, msg)

            return None

        active_subs = []
        canceled_subs = []
        for customer in queryset:
            subs = customer.subscriptions.all()
            for sub in subs:
                if sub.state == Subscription.STATES.ACTIVE:
                    active_subs.append(sub)
                elif sub.state == Subscription.STATES.CANCELED:
                    canceled_subs.append(sub)

        if len(active_subs) + len(canceled_subs) == 0:
            msg = 'The user does not have any active or canceled documents.'
            self.message_user(request, msg, level=messages.WARNING)
            return None

        context = {
            'title': _('Are you sure?'),
            'active_subscriptions': active_subs,
            'canceled_subscriptions': canceled_subs,
            'queryset': queryset,
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
            'opts': self.model._meta

        }
        return render(request, 'admin/issue_all_customer_documents.html', context)

    generate_all_documents.short_description = 'Generate all user\'s Invoices and Proformas'


class ProviderAdmin(LiveModelAdmin):
    fields = ['company', 'name', 'email', 'address_1', 'address_2', 'city',
              'state', 'zip_code', 'country', 'flow', 'invoice_series',
              'invoice_starting_number', 'proforma_series',
              'proforma_starting_number', 'default_document_state',
              'generate_documents_on_trial_end', 'separate_cycles_during_trial', 'prebill_plan',
              'cycle_billing_duration', 'extra', 'meta']
    list_display = ['name', 'invoice_series_list_display',
                    'proforma_series_list_display', metadata]
    search_fields = ['name', 'company', 'address_1', 'address_2', 'city', 'zip_code', 'country',
                     'state', 'email', 'meta']
    actions = ['generate_monthly_totals']
    exclude = ['live']

    def invoice_series_list_display(self, obj):
        return '{}-{}'.format(obj.invoice_series, obj.invoice_starting_number)

    invoice_series_list_display.short_description = 'Invoice series starting number'

    def proforma_series_list_display(self, obj):
        return '{}-{}'.format(obj.proforma_series,
                              obj.proforma_starting_number)

    proforma_series_list_display.short_description = 'Proforma series starting number'

    def _compute_monthly_totals(self, model_klass, provider, documents):
        klass_name_plural = model_klass.__name__ + 's'

        totals = {}
        totals[klass_name_plural] = OrderedDict()

        documents = documents.filter(provider=provider)

        documents_months_years = documents.order_by().annotate(
            month=ExtractMonth('issue_date'),
            year=ExtractYear('issue_date'),
        ).filter(
            provider=provider
        ).values_list(
            'month', 'year'
        ).distinct()

        totals[klass_name_plural]['entries'] = OrderedDict()
        documents_years_months = sorted((year, month)
                                        for month, year in documents_months_years
                                        if month and year)

        documents_currencies = set(
            documents.filter(provider=provider).values_list("currency", flat=True).distinct()
        )

        unpaid_documents = documents.filter(state=BillingDocumentBase.STATES.DRAFT)
        draft_totals = totals[klass_name_plural]['draft'] = defaultdict(Decimal)

        for doc in unpaid_documents:
            draft_totals[doc.currency] += doc.total

        totals[klass_name_plural]['currencies'] = documents_currencies

        for year_month in documents_years_months:
            if year_month is None:
                continue
            display_date = date(day=1, month=year_month[1], year=year_month[0]).strftime('%B %Y')
            totals[klass_name_plural]['entries'][display_date] = defaultdict(Decimal)

            documents_from_month = documents.filter(
                state__in=[BillingDocumentBase.STATES.ISSUED, BillingDocumentBase.STATES.PAID],
                issue_date__month=year_month[1],
                issue_date__year=year_month[0]
            )
            totals_per_date = totals[klass_name_plural]['entries'][display_date]

            for doc in documents_from_month:
                totals_per_date['total_' + doc.currency] += doc.total

                if doc.state == BillingDocumentBase.STATES.ISSUED:
                    totals_per_date['unpaid_' + doc.currency] += doc.total

                if doc.state == BillingDocumentBase.STATES.PAID:
                    totals_per_date['paid_' + doc.currency] += doc.total

            totals[klass_name_plural]['entries'][display_date] = {
                total_key: str(total_value) for total_key, total_value in totals_per_date.items()
            }

        return totals

    def generate_monthly_totals(self, request, queryset):
        totals = {}

        invoices = Invoice.objects.filter(
            provider__in=queryset,
            state__in=[BillingDocumentBase.STATES.DRAFT,
                       BillingDocumentBase.STATES.ISSUED,
                       BillingDocumentBase.STATES.PAID]
        )

        proformas = Proforma.objects.filter(
            provider__in=queryset,
            state__in=[BillingDocumentBase.STATES.DRAFT,
                       BillingDocumentBase.STATES.ISSUED,
                       BillingDocumentBase.STATES.PAID]
        )

        for provider in queryset:
            totals[provider.name] = OrderedDict()
            invoices_total = self._compute_monthly_totals(Invoice, provider,
                                                          invoices)
            totals[provider.name].update(invoices_total)

            proformas_total = self._compute_monthly_totals(Proforma, provider,
                                                           proformas)
            totals[provider.name].update(proformas_total)

        context = {
            'title': _('Monthly totals'),
            'totals': totals,
            'queryset': queryset,
            'opts': self.model._meta,
        }

        return render(request, 'admin/monthly_totals.html', context)

    generate_monthly_totals.short_description = 'Generate monthly totals'


class DocumentEntryForm(forms.ModelForm):
    class Meta:
        model = DocumentEntry
        fields = ('description', 'prorated', 'product_code', 'unit',
                  'unit_price', 'quantity', 'start_date', 'end_date')
        widgets = {
            'description': forms.Textarea(attrs={'cols': 50, 'rows': 3})
        }


class DocumentEntryInline(TabularInline):
    model = DocumentEntry
    form = DocumentEntryForm
    extra = 0


class BillingDocumentForm(forms.ModelForm):
    transaction_currency = ChoiceField(
        choices=(BLANK_CHOICE_DASH + list(currencies)), required=False,
    )

    def __init__(self, *args, **kwargs):
        # If it's an edit action, save the provider and the number. Check the
        # save() method to see their usefulness.
        instance = kwargs.get('instance')
        self.initial_number = instance.number if instance else None
        self.initial_series = instance.series if instance else None
        self.provider = instance.provider if instance else None

        super(BillingDocumentForm, self).__init__(*args, **kwargs)

    def clean(self, *args, **kwargs):
        cleaned_data = super(BillingDocumentForm, self).clean(*args, **kwargs)

        customer = cleaned_data.get('customer', None)
        if not customer:
            return cleaned_data

        currency = cleaned_data['currency']

        cleaned_data['transaction_currency'] = (
            cleaned_data['transaction_currency'] or customer.currency or currency
        )

        if self.instance:
            self.instance.transaction_currency = cleaned_data['transaction_currency']

        return cleaned_data

    def save(self, commit=True, *args, **kwargs):
        obj = super(BillingDocumentForm, self).save(commit=False)
        # The provider has changed => generate a new number which corresponds
        # to new provider's count
        if self.provider != obj.provider:
            obj.number = None
        else:
            # If the number input box was just cleaned => place back the
            # old number. This will prevent from having unused numbers.
            if self.initial_number and not obj.number:
                if (obj.series and self.initial_series and
                        obj.series == self.initial_series):
                    obj.number = self.initial_number

        if commit:
            obj.save()
        return obj


class InvoiceForm(BillingDocumentForm):
    class Meta:
        model = Invoice
        # NOTE: The exact fields fill be added in the InvoiceAdmin. This was
        # added here to remove the deprecation warning.
        fields = ()
        widgets = {
            'provider': autocomplete.ModelSelect2(
                url='autocomplete-provider'
            ),
            'customer': autocomplete.ModelSelect2(
                url='autocomplete-customer'
            ),
        }


class ProformaForm(BillingDocumentForm):
    class Meta:
        model = Proforma
        # NOTE: The exact fields fill be added in the ProformaAdmin. This was
        # added here to remove the deprecation warning.
        fields = ()
        widgets = {
            'provider': autocomplete.ModelSelect2(
                url='autocomplete-provider'
            ),
            'customer': autocomplete.ModelSelect2(
                url='autocomplete-customer'
            ),
        }


class DueDateFilter(SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = 'due date'

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'due_date_filter'

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return (
            ('due_this_month', _('All due this month')),
            ('due_today', _('All due today')),
            ('overdue_since_last_month', _('All overdue since last month')),
            ('overdue', _('All overdue'))
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        # Compare the requested value (either '80s' or '90s')
        # to decide how to filter the queryset.
        if self.value() == 'due_this_month':
            return queryset.due_this_month()
        if self.value() == 'due_today':
            return queryset.due_today()
        if self.value() == 'overdue_since_last_month':
            return queryset.overdue_since_last_month()
        if self.value() == 'overdue':
            return queryset.overdue()

        return queryset


class InvoiceFilter(SimpleListFilter):
    title = _('invoice')
    parameter_name = 'invoice'

    def lookups(self, request, model_admin):
        queryset = model_admin.get_queryset(request)

        invoices_queryset = Invoice.objects \
            .filter(invoice_transactions__in=queryset.distinct()) \
            .annotate(_series_number=Concat(F('series'), Value('-'), F('number'),
                                            output_field=fields.CharField())) \
            .values_list('id', '_series_number') \
            .distinct()

        return list(invoices_queryset)

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(invoice__exact=self.value())
        return queryset


class ProformaFilter(SimpleListFilter):
    title = _('proforma')
    parameter_name = 'proforma'

    def lookups(self, request, model_admin):
        queryset = model_admin.get_queryset(request)

        proformas_queryset = Proforma.objects \
            .filter(proforma_transactions__in=queryset.distinct()) \
            .annotate(_series_number=Concat(F('series'), Value('-'), F('number'),
                                            output_field=fields.CharField())) \
            .values_list('id', '_series_number') \
            .distinct()

        return list(proformas_queryset)

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(proforma__exact=self.value())
        return queryset


class BillingDocumentAdmin(ModelAdmin):
    list_display = ['series_number', 'get_customer', 'state',
                    'get_provider', 'issue_date', 'due_date', 'paid_date',
                    'cancel_date', tax, 'total', 'transactions', 'is_storno',
                    'get_related_document']

    list_filter = ('provider__company', 'state', 'customer', DueDateFilter, 'is_storno')

    common_fields = ['company', 'address_1', 'address_2', 'city',
                     'country', 'zip_code', 'state', 'email']
    customer_search_fields = ['customer__{field}'.format(field=field)
                              for field in common_fields + ['first_name', 'last_name']]
    provider_search_fields = ['provider__{field}'.format(field=field)
                              for field in common_fields + ['name']]
    search_fields = (customer_search_fields + provider_search_fields +
                     ['series', 'number', '_total', '_total_in_transaction_currency'])

    date_hierarchy = 'issue_date'

    fields = (('series', 'number'), 'provider', 'customer', 'issue_date',
              'due_date', 'paid_date', 'cancel_date',
              ('sales_tax_name', 'sales_tax_percent'), 'currency',
              ('transaction_currency', 'transaction_xe_rate'),
              'transaction_xe_date', ('state', 'is_storno'), 'total', 'get_related_document')
    readonly_fields = ('state', 'total', 'get_related_document', 'is_storno')
    inlines = [DocumentEntryInline]
    actions = ['issue', 'pay', 'cancel', 'clone', 'download_selected_documents',
               'mark_pdf_for_generation']

    def get_queryset(self, request):
        return super(BillingDocumentAdmin, self).get_queryset(request) \
                                                .select_related('related_document',
                                                                'customer',
                                                                'provider',
                                                                'pdf')

    def get_search_results(self, request, queryset, search_term):
        if '-' in search_term and search_term[-1].isdigit():
            return queryset \
                .annotate(_series_number=Concat(F('series'), Value('-'), F('number'),
                                                output_field=fields.CharField())) \
                .filter(_series_number=search_term), True

        return super(BillingDocumentAdmin, self).get_search_results(request, queryset, search_term)

    @property
    def _model(self):
        raise NotImplementedError

    @property
    def _model_name(self):
        raise NotImplementedError

    def _call_method_on_queryset(self, request, method, queryset, action):
        results = {}
        for document in queryset:
            results[document] = {}
            try:
                results[document]['success'] = True
                results[document]['result'] = method(document)

                document.save()

                LogEntry.objects.log_action(
                    user_id=request.user.id,
                    content_type_id=ContentType.objects.get_for_model(document).pk,
                    object_id=document.id,
                    object_repr=force_text(document),
                    action_flag=CHANGE,
                    change_message='{action} action initiated by user.'.format(
                        action=action.replace('_', ' ').strip().capitalize()
                    )
                )
            except TransitionNotAllowed as error:
                results[document]['result'] = mark_safe(error)
                results[document]['success'] = False
            except ValueError as error:
                results[document]['result'] = force_text(error)
                results[document]['success'] = False
            except AttributeError:
                results[document]['success'] = False
                results[document]['result'] = ""

        return results

    def _parse_results_into_messages(self, results):
        parsed_results = []
        for document, result in results.items():
            message, info = "", ""

            if result['success'] and result['result'] or not result['success']:
                message = document.admin_change_url

                if result['result']:
                    info = getattr(result['result'], 'admin_change_url',
                                   conditional_escape(result['result']))
            if message:
                if result:
                    message += ": " + info
                parsed_results.append(message)

        return parsed_results

    def perform_action(self, request, queryset, action,
                       readable_action=None, readable_past_action=None):
        method = getattr(self._model, action, None)
        if not method:
            self.message_user(request, 'Illegal action.', level=messages.ERROR)
            return

        readable_action = readable_action or action.replace('_', ' ').strip()
        readable_past_action = (readable_past_action if readable_past_action else
                                "executed {action}".format(action=action))

        results = self._call_method_on_queryset(request, method, queryset, action)
        error_results = {document: result for document, result in results.items()
                         if not result['success']}
        success_results = {document: result for document, result in results.items()
                           if result['success']}

        error_results_count, success_results_count = len(error_results), len(success_results)

        model_name = self._model_name.lower()
        model_name_plural = model_name + "s"

        success_message, error_message = "", ""
        if success_results_count:
            documents_pluralization = model_name_plural if success_results_count else model_name

            success_message = "Successfully {readable_past_action} {count} " \
                "{documents_pluralization}".format(
                    readable_past_action=readable_past_action, count=success_results_count,
                    documents_pluralization=documents_pluralization
                )

            success_results_messages = self._parse_results_into_messages(success_results)
            if success_results_messages:
                success_message += ":<br/>" + "<br/>".join(success_results_messages)

        if error_results_count:
            documents_pluralization = model_name_plural if error_results_count else model_name

            error_message = "Couldn't {readable_action} {count} {documents_pluralization}".format(
                readable_action=readable_action, count=error_results_count,
                documents_pluralization=documents_pluralization
            )

            error_results_messages = self._parse_results_into_messages(error_results)
            error_message += ":<br/>" + "<br/>".join(error_results_messages)

        if error_message:
            self.message_user(request, mark_safe(error_message), level=messages.ERROR)
        if success_message:
            self.message_user(request, mark_safe(success_message))

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return False

    def get_actions(self, request):
        actions = super(BillingDocumentAdmin, self).get_actions(request)
        if not request.user.is_superuser:
            if 'delete_selected' in actions:
                del actions['delete_selected']
        return actions

    def total(self, obj):
        return '{:.2f} {currency}'.format(obj.total, currency=obj.currency)

    total.admin_order_field = '_total'

    def transactions(self, obj):
        if obj.transaction_xe_rate:
            url_base = 'admin:silver_transaction_changelist'

            url = furl(reverse(url_base))
            url.add(args={obj.__class__.__name__.lower() + "__id__exact": obj.pk})

            return '<a href="{url}" target="_blank">{total:.2f} {currency}</a>'.format(
                url=url.url, total=obj.total_in_transaction_currency,
                currency=obj.transaction_currency
            )

        return None

    transactions.allow_tags = True
    transactions.admin_order_field = '_total_in_transaction_currency'

    def _download_pdf(self, url, base_path):
        local_file_path = os.path.join(base_path, 'billing-temp-document.pdf')
        response = requests.get(url)
        response.encoding = 'utf-8'

        with open(local_file_path, 'wb') as out_file:
            content = response.content
            pdf_header_pos = content.find(b'%PDF-')
            if pdf_header_pos > 0:
                content = content[pdf_header_pos:]
            out_file.write(content)
            out_file.flush()

        return local_file_path

    def download_selected_documents(self, request, queryset):
        # NOTE (important): this works only if the pdf is not stored on local
        # disk as it is fetched via HTTP
        now = timezone.now()

        queryset = queryset.filter(
            state__in=[BillingDocumentBase.STATES.ISSUED,
                       BillingDocumentBase.STATES.CANCELED,
                       BillingDocumentBase.STATES.PAID]
        )

        base_path = '/tmp'
        merger = PdfFileMerger()
        for document in queryset:
            if document.pdf:
                local_file_path = self._download_pdf(document.pdf.url, base_path)
                try:
                    reader = PdfFileReader(open(local_file_path, 'rb'))
                    merger.append(reader)
                    logging_ctx = {
                        'number': document.series_number,
                        'status': 'ok'
                    }
                except Exception as e:
                    logging_ctx = {
                        'number': document.series_number,
                        'status': 'failed',
                        'error': e
                    }

                logger.debug('Admin aggregate PDF generation: %s', logging_ctx)

                try:
                    os.remove(local_file_path)
                except OSError as e:
                    if e.errno != errno.ENOENT:
                        raise

        response = HttpResponse(content_type='application/pdf')
        filename = 'Billing-Documents-{now}.pdf'.format(now=now)
        content_disposition = 'attachment; filename="{fn}'.format(fn=filename)
        response['Content-Disposition'] = content_disposition

        merger.write(response)
        merger.close()

        return response

    download_selected_documents.short_description = 'Download selected documents'

    def get_related_document(self, obj):
        return obj.related_document.admin_change_url if obj.related_document else None

    get_related_document.short_description = 'Related doc'
    get_related_document.allow_tags = True

    def get_customer(self, obj):
        return obj.customer.admin_change_url

    get_customer.allow_tags = True
    get_customer.short_description = "customer"
    get_customer.admin_order_field = "customer"

    def get_provider(self, obj):
        return obj.provider.admin_change_url

    get_provider.allow_tags = True
    get_provider.short_description = "provider"
    get_provider.admin_order_field = "provider"


class InvoiceDocumentEntryInline(DocumentEntryInline):
    fk_name = 'invoice'


class InvoiceAdmin(BillingDocumentAdmin):
    form = InvoiceForm
    list_display = BillingDocumentAdmin.list_display + [
        'get_invoice_pdf',
    ]
    inlines = [InvoiceDocumentEntryInline]
    actions = BillingDocumentAdmin.actions + ['create_storno']

    def issue(self, request, queryset):
        self.perform_action(request, queryset, 'issue', readable_past_action='issued')

    issue.short_description = 'Issue the selected invoice(s)'

    def pay(self, request, queryset):
        self.perform_action(request, queryset, 'pay', readable_past_action='paid')

    pay.short_description = 'Pay the selected invoice(s)'

    def cancel(self, request, queryset):
        self.perform_action(request, queryset, 'cancel', readable_past_action='canceled')

    cancel.short_description = 'Cancel the selected invoice(s)'

    def create_storno(self, request, queryset):
        self.perform_action(request, queryset, 'create_storno', readable_action='create storno for',
                            readable_past_action='created storno for')

    create_storno.short_description = 'Generate storno(s) for the selected invoice(s)'

    def clone(self, request, queryset):
        self.perform_action(request, queryset, 'clone_into_draft',
                            readable_action='generate draft clones for',
                            readable_past_action='generated draft clones for')

    clone.short_description = 'Clone the selected invoice(s) into draft'

    def mark_pdf_for_generation(self, request, queryset):
        self.perform_action(request, queryset, 'mark_for_generation',
                            readable_past_action='marked for generation')

    mark_pdf_for_generation.short_description = 'Mark the selected invoice(s) for PDF generation'

    def get_invoice_pdf(self, invoice):
        if invoice.pdf:
            url = reverse('invoice-pdf', kwargs={'invoice_id': invoice.id})
            return '<a href="{url}" target="_blank">Download</a>'.format(url=url)
        else:
            return None

    get_invoice_pdf.short_description = "PDF"
    get_invoice_pdf.allow_tags = True

    @property
    def _model(self):
        return Invoice

    @property
    def _model_name(self):
        return "Invoice"


class ProformaDocumentEntryInline(DocumentEntryInline):
    fk_name = 'proforma'


class ProformaAdmin(BillingDocumentAdmin):
    form = ProformaForm
    list_display = BillingDocumentAdmin.list_display + [
        'get_proforma_pdf',
    ]
    inlines = [ProformaDocumentEntryInline]
    actions = BillingDocumentAdmin.actions + ['create_invoice']

    def issue(self, request, queryset):
        self.perform_action(request, queryset, 'issue')

    issue.short_description = 'Issue the selected proforma(s)'

    def create_invoice(self, request, queryset):
        self.perform_action(request, queryset, 'create_invoice')

    create_invoice.short_description = 'Create invoice from proforma(s)'

    def pay(self, request, queryset):
        self.perform_action(request, queryset, 'pay')

    pay.short_description = 'Pay the selected proforma(s)'

    def cancel(self, request, queryset):
        self.perform_action(request, queryset, 'cancel')

    cancel.short_description = 'Cancel the selected proforma(s)'

    def clone(self, request, queryset):
        self.perform_action(request, queryset, 'clone_into_draft')

    clone.short_description = 'Clone the selected proforma(s) into draft'

    def mark_pdf_for_generation(self, request, queryset):
        self.perform_action(request, queryset, 'mark_for_generation')

    mark_pdf_for_generation.short_description = 'Mark the selected proforma(s) for PDF generation'

    def get_proforma_pdf(self, proforma):
        if proforma.pdf:
            url = reverse('proforma-pdf', kwargs={'proforma_id': proforma.id})
            return '<a href="{url}" target="_blank">Download</a>'.format(url=url)
        else:
            return None

    get_proforma_pdf.short_description = "PDF"
    get_proforma_pdf.allow_tags = True

    @property
    def _model(self):
        return Proforma

    @property
    def _model_name(self):
        return "Proforma"


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['proforma', 'invoice', 'amount', 'currency', 'state',
                  'payment_method', 'uuid', 'valid_until', 'last_access',
                  'data', 'fail_code', 'cancel_code', 'refund_code']

        readonly_fields = ['state', 'uuid', 'last_access']
        create_only_fields = ['amount', 'currency', 'proforma', 'invoice',
                              'payment_method', 'valid_until']

        widgets = {
            'invoice': autocomplete.ModelSelect2(
                url='autocomplete-invoice'
            ),
            'proforma': autocomplete.ModelSelect2(
                url='autocomplete-proforma'
            ),
            'payment_method': autocomplete.ModelSelect2(
                url='autocomplete-payment-method'
            ),

        }

    def __init__(self, *args, **kwargs):
        super(TransactionForm, self).__init__(*args, **kwargs)

        if 'amount' in self.fields:
            self.fields['amount'].required = False
        if 'currency' in self.fields:
            self.fields['currency'].required = False

    def clean(self):
        if ((self.cleaned_data['amount'] and not self.cleaned_data['currency']) or
                (self.cleaned_data['amount'] is None and self.cleaned_data['currency'])):
            raise ValidationError('You must either specify both amount and currency fields or '
                                  'leave them both blank.')

        document = self.cleaned_data['proforma'] or self.cleaned_data['invoice']
        if not self.cleaned_data['currency']:
            self.cleaned_data['amount'] = document.amount_to_be_charged_in_transaction_currency
            self.cleaned_data['currency'] = document.transaction_currency

        return self.cleaned_data


class TransactionAdmin(ModelAdmin):
    form = TransactionForm

    list_display = ('uuid', 'related_invoice', 'related_proforma',
                    'amount', 'state', 'created_at', 'updated_at',
                    'get_customer', 'get_pay_url', 'get_payment_method',
                    'get_is_recurring')
    list_filter = ('payment_method__customer', 'state', 'payment_method__payment_processor',
                   ProformaFilter, InvoiceFilter)
    actions = ['execute', 'process', 'cancel', 'settle', 'fail']
    ordering = ['-created_at']

    def get_queryset(self, request):
        return super(TransactionAdmin, self).get_queryset(request) \
                                            .select_related('payment_method__customer',
                                                            'invoice', 'proforma')

    def get_readonly_fields(self, request, instance=None):
        if instance:
            return self.form.Meta.readonly_fields + self.form.Meta.create_only_fields
        return self.form.Meta.readonly_fields

    def get_pay_url(self, obj):
        return u'<a href="%s">%s</a>' % (get_payment_url(obj, None),
                                         obj.payment_processor)

    get_pay_url.allow_tags = True
    get_pay_url.short_description = 'Pay URL'

    def get_customer(self, obj):
        return obj.customer.admin_change_url

    get_customer.allow_tags = True
    get_customer.short_description = 'Customer'
    get_customer.admin_order_field = 'customer'

    def get_is_recurring(self, obj):
        return obj.payment_method.verified

    get_is_recurring.boolean = True
    get_is_recurring.short_description = 'Recurring'

    def get_payment_method(self, obj):
        link = reverse("admin:silver_paymentmethod_change", args=[obj.payment_method.pk])
        return u'<a href="%s">%s</a>' % (link, obj.payment_method)

    get_payment_method.allow_tags = True
    get_payment_method.short_description = 'Payment Method'

    def perform_action(self, request, queryset, action, display_verb=None):
        failed_count = 0
        transactions_count = len(queryset)

        if action not in self.actions:
            self.message_user(request, 'Illegal action.', level=messages.ERROR)
            return

        method = getattr(Transaction, action)

        for transaction in queryset:
            try:
                method(transaction)
                transaction.save()
            except TransitionNotAllowed:
                failed_count += 1

        settled_count = transactions_count - failed_count

        if not failed_count:
            self.message_user(
                request,
                'Successfully %s %d transactions.' % (
                    display_verb or action, transactions_count
                )
            )
        elif failed_count != transactions_count:

            self.message_user(
                request,
                '%s %d transactions, %d failed.' % (
                    display_verb or action, settled_count, failed_count
                ),
                level=messages.WARNING
            )
        else:
            self.message_user(
                request,
                'Couldn\'t %s any of the selected transactions.' % action,
                level=messages.ERROR
            )

        action = action.capitalize()

        logger.info('[Admin][%s Transaction]: %s', action, {
            'detail': '%s Transaction action initiated by user.' % action,
            'user_id': request.user.id,
            'user_staff': request.user.is_staff,
            'failed_count': failed_count,
            'settled_count': settled_count
        })

    def execute(self, request, queryset):
        failed_count = 0
        transactions_count = len(queryset)

        for transaction in queryset:
            try:
                payment_processor = transaction.payment_method.get_payment_processor()
                if payment_processor.type != PaymentProcessorTypes.Triggered:
                    continue
                payment_processor.process_transaction(transaction)
            except Exception:
                failed_count += 1
                logger.error('Encountered exception while executing transaction '
                             'with id=%s.', transaction.id, exc_info=True)

        settled_count = transactions_count - failed_count

        if not failed_count:
            self.message_user(
                request,
                'Successfully executed %d transactions.' % (transactions_count)
            )
        elif failed_count != transactions_count:
            self.message_user(
                request,
                'Executed %d transactions, %d failed.' % (
                    settled_count, failed_count
                ),
                level=messages.WARNING
            )
        else:
            self.message_user(
                request,
                'Couldn\'t execute any of the selected transactions.',
                level=messages.ERROR
            )

        logger.info('[Admin][%s Transaction]: Execute', {
            'detail': 'Execute Transaction action initiated by user.',
            'user_id': request.user.id,
            'user_staff': request.user.is_staff,
            'failed_count': failed_count,
            'settled_count': settled_count
        })

    execute.short_description = 'Execute the selected transactions'

    def process(self, request, queryset):
        self.perform_action(request, queryset, 'process', 'processed')

    process.short_description = 'Process the selected transactions'

    def cancel(self, request, queryset):
        self.perform_action(request, queryset, 'cancel', 'canceled')

    cancel.short_description = 'Cancel the selected transactions'

    def settle(self, request, queryset):
        self.perform_action(request, queryset, 'settle', 'settled')

    settle.short_description = 'Settle the selected transactions'

    def fail(self, request, queryset):
        self.perform_action(request, queryset, 'fail', 'failed')

    fail.short_description = 'Fail the selected transactions'

    def related_invoice(self, obj):
        return obj.invoice.admin_change_url if obj.invoice else None

    related_invoice.allow_tags = True
    related_invoice.short_description = 'Invoice'

    def related_proforma(self, obj):
        return obj.proforma.admin_change_url if obj.proforma else None

    related_proforma.allow_tags = True
    related_proforma.short_description = 'Proforma'


class PaymentMethodAdmin(ModelAdmin):
    list_display = ('customer', 'payment_processor', 'added_at', 'verified',
                    'canceled')
    list_filter = ('customer', 'verified', 'canceled',
                   'payment_processor')
    search_fields = ['customer__first_name', 'customer__last_name',
                     'customer__company']


site.register(Transaction, TransactionAdmin)
site.register(PaymentMethod, PaymentMethodAdmin)
site.register(Plan, PlanAdmin)
site.register(Subscription, SubscriptionAdmin)
site.register(Customer, CustomerAdmin)
site.register(Provider, ProviderAdmin)
site.register(Invoice, InvoiceAdmin)
site.register(Proforma, ProformaAdmin)
site.register(ProductCode)
site.register(MeteredFeature)
