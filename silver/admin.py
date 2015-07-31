from django import forms
from django.contrib import admin, messages
from django.utils.html import escape
from django_fsm import TransitionNotAllowed
from django.core.urlresolvers import reverse

from models import (Plan, MeteredFeature, Subscription, Customer, Provider,
                    MeteredFeatureUnitsLog, Invoice, DocumentEntry,
                    ProductCode, Proforma, BillingLog)

from django.contrib.admin.actions import delete_selected as delete_selected_

from django.utils.translation import ugettext_lazy


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


class LiveModelAdmin(admin.ModelAdmin):
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

    delete_selected.short_description = ugettext_lazy("Delete selected "
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


class PlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'interval_display',
                    'trial_period_days', 'enabled', 'private']
    search_fields = ['name']
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


class MeteredFeatureUnitsLogInLine(admin.TabularInline):
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


class BillingLogInLine(admin.TabularInline):
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


class SubscriptionAdmin(admin.ModelAdmin):
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
        self.perform_action(request, 'activate_and_issue_billing_doc', queryset)
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
    exclude = ['live']

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
    exclude = ['live']

    def invoice_series_list_display(self, obj):
        return '{}-{}'.format(obj.invoice_series, obj.invoice_starting_number)
    invoice_series_list_display.short_description = 'Invoice series starting number'

    def proforma_series_list_display(self, obj):
        return '{}-{}'.format(obj.proforma_series,
                              obj.proforma_starting_number)
    proforma_series_list_display.short_description = 'Proforma series starting number'


class DocumentEntryInline(admin.TabularInline):
    model = DocumentEntry
    fields = ('description', 'prorated', 'product_code', 'unit', 'unit_price',
              'quantity', 'start_date', 'end_date')
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


class BillingDocumentAdmin(admin.ModelAdmin):
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
    actions = ['issue', 'pay', 'cancel', 'clone']

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

admin.site.register(Plan, PlanAdmin)
admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(Customer, CustomerAdmin)
admin.site.register(Provider, ProviderAdmin)
admin.site.register(Invoice, InvoiceAdmin)
admin.site.register(Proforma, ProformaAdmin)
admin.site.register(ProductCode)
admin.site.register(MeteredFeature)
