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


import os
import errno
import logging
from collections import OrderedDict

import requests
from django import forms
from django.contrib import messages
from django.contrib.admin import helpers, site, TabularInline, ModelAdmin
from django.contrib.admin.actions import delete_selected as delete_selected_
from django.contrib.admin.models import LogEntry, CHANGE
from django.contrib.contenttypes.models import ContentType
from django.db import connections
from django.utils.html import escape
from django_fsm import TransitionNotAllowed
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from django.shortcuts import render
from django.http import HttpResponse
from PyPDF2 import PdfFileReader, PdfFileMerger

from models import (Plan, MeteredFeature, Subscription, Customer, Provider,
                    MeteredFeatureUnitsLog, Invoice, DocumentEntry,
                    ProductCode, Proforma, BillingLog, BillingDocument)
from documents_generator import DocumentsGenerator

logger = logging.getLogger(__name__)


def metadata(obj):
    d = u'(None)'
    if obj.meta:
        d = u''
        for key, value in obj.meta.iteritems():
            d += u'%s: <code>%s</code><br>' % (escape(key), escape(value))
    return d
metadata.allow_tags = True


def tax(obj):
    return ("{} {:.2f}%".format(obj.sales_tax_name, obj.sales_tax_percent)
            if obj.sales_tax_percent > 0 else '')
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
                  'generate_after', 'metered_features', 'enabled', 'private')

    def clean(self):
        metered_features = self.cleaned_data.get('metered_features')
        Plan.validate_metered_features(metered_features)
        return self.cleaned_data


class PlanAdmin(ModelAdmin):
    list_display = ['name', 'description', 'interval_display',
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


class MeteredFeatureUnitsLogInLine(TabularInline):
    model = MeteredFeatureUnitsLog
    list_display = ['metered_feature']
    readonly_fields = ('start_date', 'end_date', )
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
    fields = ['billing_date', 'proforma_link', 'invoice_link']
    readonly_fields = ['billing_date', 'proforma_link', 'invoice_link']
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


class SubscriptionAdmin(ModelAdmin):
    list_display = ['customer', 'plan', 'last_billing_date', 'trial_end',
                    'start_date', 'ended_at', 'state', metadata]
    list_filter = ['plan', 'state', 'plan__provider', 'customer']
    readonly_fields = ['state', ]
    actions = ['activate', 'cancel_now', 'cancel_at_end_of_cycle', 'end']
    search_fields = ['customer__name', 'customer__company', 'plan__name',
                     'meta']
    inlines = [MeteredFeatureUnitsLogInLine, BillingLogInLine]

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
                    object_repr=unicode(entry),
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
    cancel_at_end_of_cycle.short_description = 'Cancel the '\
        'selected Subscription(s) at the end '\
        'of the billing cycle'

    def end(self, request, queryset):
        self.perform_action(request, 'end', queryset)
    end.short_description = 'End the selected Subscription(s) '


class CustomerAdmin(LiveModelAdmin):
    fields = ['company', 'name', 'customer_reference', 'email', 'address_1',
              'address_2', 'city', 'state', 'zip_code', 'country',
              'consolidated_billing', 'payment_due_days', 'sales_tax_name',
              'sales_tax_percent', 'sales_tax_number', 'extra', 'meta']
    list_display = ['__unicode__', 'customer_reference',
                    tax, 'consolidated_billing', metadata]
    search_fields = ['customer_reference', 'name', 'company', 'address_1',
                     'address_2', 'city', 'zip_code', 'country', 'state',
                     'email', 'meta']
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
              'proforma_starting_number', 'default_document_state', 'extra',
              'meta']
    list_display = ['__unicode__', 'invoice_series_list_display',
                    'proforma_series_list_display', metadata]
    search_fields = ['customer_reference', 'name', 'company', 'address_1',
                     'address_2', 'city', 'zip_code', 'country', 'state',
                     'email', 'meta']
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

        all_documents = documents.filter(provider=provider)
        paid_documents = documents.filter(
            provider=provider,
            state=BillingDocument.STATES.PAID
        )
        documents_months = documents.order_by().filter(
            provider=provider
        ).values(
            'month'
        ).distinct()

        total_draft = sum(
            doc.total for doc in (
                documents.filter(
                    provider=provider,
                    state=BillingDocument.STATES.DRAFT
                )
            )
        )

        totals[klass_name_plural]['draft_total'] = str(total_draft)
        totals[klass_name_plural]['entries'] = OrderedDict()
        documents_months = sorted([month['month']
                                   for month in documents_months
                                   if month['month']])
        for month_value in documents_months:
            if month_value is None:
                continue
            display_date = month_value.strftime('%B %Y')
            totals[klass_name_plural]['entries'][display_date] = OrderedDict()

            all_documents_from_month = all_documents.filter(
                issue_date__month=month_value.month,
                issue_date__year=month_value.year
            )
            paid_documents_from_month = paid_documents.filter(
                issue_date__month=month_value.month,
                issue_date__year=month_value.year
            )
            total = sum(invoice.total for invoice in all_documents_from_month)
            total_paid = sum(invoice.total for invoice in paid_documents_from_month)
            totals[klass_name_plural]['entries'][display_date]['total'] = str(total)
            totals[klass_name_plural]['entries'][display_date]['paid'] = str(total_paid)
            totals[klass_name_plural]['entries'][display_date]['unpaid'] = str(total - total_paid)

        return totals

    def generate_monthly_totals(self, request, queryset):
        totals = {}

        invoices = Invoice.objects.extra(
            select={
                'month': connections[Invoice.objects.db].ops.date_trunc_sql(
                    'month', 'issue_date'
                )
            }
        ).filter(
            provider__in=queryset,
            state__in=[BillingDocument.STATES.DRAFT,
                       BillingDocument.STATES.ISSUED,
                       BillingDocument.STATES.PAID]
        )

        proformas = Proforma.objects.extra(
            select={
                'month': connections[Invoice.objects.db].ops.date_trunc_sql(
                    'month', 'issue_date'
                )
            }
        ).filter(
            provider__in=queryset,
            state__in=[BillingDocument.STATES.DRAFT,
                       BillingDocument.STATES.ISSUED,
                       BillingDocument.STATES.PAID]
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
            'opts': self.model._meta
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
    def __init__(self, *args, **kwargs):
        # If it's an edit action, save the provider and the number. Check the
        # save() method to see their usefulness.
        instance = kwargs.get('instance')
        self.initial_number = instance.number if instance else None
        self.initial_series = instance.series if instance else None
        self.provider = instance.provider if instance else None

        super(BillingDocumentForm, self).__init__(*args, **kwargs)

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


class ProformaForm(BillingDocumentForm):
    class Meta:
        model = Proforma
        # NOTE: The exact fields fill be added in the ProformaAdmin. This was
        # added here to remove the deprecation warning.
        fields = ()


class BillingDocumentAdmin(ModelAdmin):
    list_display = ['series_number', 'customer', 'state',
                    'provider', 'issue_date', 'due_date', 'paid_date',
                    'cancel_date', tax, 'total']

    list_filter = ('provider__company', 'state')

    common_fields = ['company', 'email', 'address_1', 'address_2', 'city',
                     'country', 'zip_code', 'name', 'state']
    customer_search_fields = ['customer__{field}'.format(field=field)
                              for field in common_fields]
    provider_search_fields = ['provider__{field}'.format(field=field)
                              for field in common_fields]
    search_fields = (customer_search_fields + provider_search_fields +
                     ['series', 'number'])

    date_hierarchy = 'issue_date'

    fields = (('series', 'number'), 'provider', 'customer', 'issue_date',
              'due_date', 'paid_date', 'cancel_date', 'sales_tax_name',
              'sales_tax_percent', 'currency', 'state', 'total')
    readonly_fields = ('state', 'total')
    inlines = [DocumentEntryInline]
    actions = ['issue', 'pay', 'cancel', 'clone', 'download_selected_documents']

    @property
    def _model(self):
        raise NotImplementedError

    @property
    def _model_name(self):
        raise NotImplementedError

    def perform_action(self, request, queryset, action):
        method = getattr(self._model, action, None)
        if not method:
            self.message_user(request, 'Illegal action.', level=messages.ERROR)
            return

        exist_failed_changes = False
        exist_failed_actions = False
        failed_changes = []
        failed_actions = []

        results = []
        for entry in queryset:
            try:
                result = method(entry)
                if result:
                    results.append(result)
                entry.save()

                LogEntry.objects.log_action(
                    user_id=request.user.id,
                    content_type_id=ContentType.objects.get_for_model(entry).pk,
                    object_id=entry.id,
                    object_repr=unicode(entry),
                    action_flag=CHANGE,
                    change_message='{action} action initiated by user.'.format(
                        action=action.replace('_', ' ').strip().capitalize()
                    )
                )
            except TransitionNotAllowed:
                exist_failed_changes = True
                failed_changes.append(entry.number)
            except ValueError as error:
                exist_failed_actions = True
                failed_actions.append(error.message)

        if exist_failed_actions:
            msg = "\n".join(failed_actions)
            self.message_user(request, msg, level=messages.ERROR)

        if exist_failed_changes:
            failed_ids = ' '.join(map(str, failed_changes))
            msg = "The state change failed for {model_name}(s) with "\
                  "numbers: {ids}".format(model_name=self._model_name.lower(),
                                          ids=failed_ids)
            self.message_user(request, msg, level=messages.ERROR)

        if not exist_failed_actions and not exist_failed_changes:
            qs_count = queryset.count()
            if action == 'clone_into_draft':
                results = ', '.join(result.series_number for result in results)
                msg = 'Successfully cloned {count} {model_name}(s) ' \
                      'into {results}.'.format(
                          model_name=self._model_name.lower(), count=qs_count,
                          results=results
                      )
            else:
                msg = 'Successfully changed {count} {model_name}(s).'.format(
                    model_name=self._model_name.lower(), count=qs_count
                )
            self.message_user(request, msg)

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
        return '{:.2f} {currency}'.format(obj.total,
                                          currency=obj.currency)

    def _download_pdf(self, url, base_path):
        local_file_path = os.path.join(base_path, 'billing-temp-document.pdf')
        response = requests.get(url, stream=True)
        should_wipe_bad_headers = True
        with open(local_file_path, 'wb') as out_file:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    if should_wipe_bad_headers:
                        pdf_header_pos = chunk.find('%PDF-')
                        if pdf_header_pos > 0:
                            # The file does not start with the '%PDF-' header
                            # => trim everything up to that position
                            chunk = chunk[pdf_header_pos:]
                        should_wipe_bad_headers = False
                    out_file.write(chunk)
                    out_file.flush()

        return local_file_path

    def download_selected_documents(self, request, queryset):
        # NOTE (important): this works only if the pdf is not stored on local
        # disk as it is fetched via HTTP
        now = timezone.now()

        queryset = queryset.filter(
            state__in=[BillingDocument.STATES.ISSUED,
                       BillingDocument.STATES.CANCELED,
                       BillingDocument.STATES.PAID]
        )

        base_path = '/tmp'
        merger = PdfFileMerger()
        for document in queryset:
            if document.pdf:
                local_file_path = self._download_pdf(document.pdf.url, base_path)
                try:
                    reader = PdfFileReader(file(local_file_path, 'rb'))
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


class InvoiceAdmin(BillingDocumentAdmin):
    form = InvoiceForm
    list_display = BillingDocumentAdmin.list_display + [
        'invoice_pdf', 'related_proforma'
    ]
    list_display_links = BillingDocumentAdmin.list_display_links
    search_fields = BillingDocumentAdmin.search_fields
    fields = BillingDocumentAdmin.fields + ('related_proforma', )
    readonly_fields = BillingDocumentAdmin.readonly_fields + (
        'related_proforma',
    )
    inlines = BillingDocumentAdmin.inlines
    actions = BillingDocumentAdmin.actions

    def issue(self, request, queryset):
        self.perform_action(request, queryset, 'issue')
    issue.short_description = 'Issue the selected invoice(s)'

    def pay(self, request, queryset):
        self.perform_action(request, queryset, 'pay')
    pay.short_description = 'Pay the selected invoice(s)'

    def cancel(self, request, queryset):
        self.perform_action(request, queryset, 'cancel')
    cancel.short_description = 'Cancel the selected invoice(s)'

    def clone(self, request, queryset):
        self.perform_action(request, queryset, 'clone_into_draft')
    clone.short_description = 'Clone the selected invoice(s) into draft'

    def invoice_pdf(self, invoice):
        if invoice.pdf:
            url = reverse('invoice-pdf', kwargs={'invoice_id': invoice.id})
            return '<a href="{url}" target="_blank">{url}</a>'.format(url=url)
        else:
            return ''
    invoice_pdf.allow_tags = True

    @property
    def _model(self):
        return Invoice

    @property
    def _model_name(self):
        return "Invoice"

    def related_proforma(self, obj):
        return obj.proforma.admin_change_url if obj.proforma else 'None'
    related_proforma.short_description = 'Related proforma'
    related_proforma.allow_tags = True


class ProformaAdmin(BillingDocumentAdmin):
    form = ProformaForm
    list_display = BillingDocumentAdmin.list_display + [
        'proforma_pdf', 'related_invoice'
    ]
    list_display_links = BillingDocumentAdmin.list_display_links
    search_fields = BillingDocumentAdmin.search_fields
    fields = BillingDocumentAdmin.fields + ('related_invoice', )
    readonly_fields = BillingDocumentAdmin.readonly_fields + (
        'related_invoice',
    )
    inlines = BillingDocumentAdmin.inlines
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

    def proforma_pdf(self, proforma):
        if proforma.pdf:
            url = reverse('proforma-pdf', kwargs={'proforma_id': proforma.id})
            return '<a href="{url}" target="_blank">{url}</a>'.format(url=url)
        else:
            return ''
    proforma_pdf.allow_tags = True

    @property
    def _model(self):
        return Proforma

    @property
    def _model_name(self):
        return "Proforma"

    def related_invoice(self, obj):
        return obj.invoice.admin_change_url if obj.invoice else 'None'
    related_invoice.short_description = 'Related invoice'
    related_invoice.allow_tags = True

site.register(Plan, PlanAdmin)
site.register(Subscription, SubscriptionAdmin)
site.register(Customer, CustomerAdmin)
site.register(Provider, ProviderAdmin)
site.register(Invoice, InvoiceAdmin)
site.register(Proforma, ProformaAdmin)
site.register(ProductCode)
site.register(MeteredFeature)
