from django import forms
from django.contrib import admin, messages
from django_fsm import TransitionNotAllowed

from models import (Plan, MeteredFeature, Subscription, Customer, Provider,
                    MeteredFeatureUnitsLog, Invoice, DocumentEntry,
                    ProductCode, Proforma)

from django.contrib.admin.actions import delete_selected as delete_selected_

from django.utils.translation import ugettext_lazy


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


class PlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'interval', 'interval_count', 'amount', 'currency',
                    'trial_period_days', 'generate_after', 'enabled', 'private']
    search_fields = ['name']


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
                     self).formfield_for_foreignkey(db_field, request, **kwargs)


class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['customer', 'plan', 'trial_end', 'start_date', 'ended_at',
                    'state', ]
    list_filter = ['plan', 'state']
    readonly_fields = ['state', ]
    actions = ['activate', 'cancel', 'end', ]
    search_fields = ['customer__name', 'customer__company', 'plan__name', ]
    inlines = [MeteredFeatureUnitsLogInLine, ]

    def perform_action(self, request, action, queryset):
        method = None
        if action == 'activate':
            method = Subscription.activate
        elif action == 'cancel':
            method = Subscription.cancel
        elif action == 'end':
            method = Subscription.end

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
        self.perform_action(request, 'activate', queryset)

    def cancel(self, request, queryset):
        self.perform_action(request, 'cancel', queryset)

    def end(self, request, queryset):
        self.perform_action(request, 'end', queryset)


class CustomerAdmin(LiveModelAdmin):
    fields = ['company', 'name', 'customer_reference', 'email', 'address_1',
              'address_2', 'city', 'state', 'zip_code', 'country',
              'consolidated_billing', 'payment_due_days', 'sales_tax_name',
              'sales_tax_percent', 'extra']
    list_display = ['customer_reference', 'name', 'company', 'email',
                    'complete_address', 'sales_tax_percent', 'sales_tax_name',
                    'consolidated_billing']
    list_display_links = list_display
    search_fields = ['customer_reference', 'name', 'company', 'address_1',
                     'address_2', 'city', 'zip_code', 'country', 'state',
                     'email']
    exclude = ['live']


class ProviderAdmin(LiveModelAdmin):
    fields = ['company', 'name', 'flow', 'invoice_series', 'invoice_starting_number',
              'proforma_series', 'proforma_starting_number', 'email',
              'address_1', 'address_2', 'city', 'state', 'zip_code', 'country',
              'extra']
    list_display = ['name', 'company', 'invoice_series', 'email', 'address_1',
                    'address_2', 'city', 'state', 'zip_code', 'country']
    list_display_links = list_display
    search_fields = list_display
    exclude = ['live']


class DocumentEntryInline(admin.TabularInline):
    model = DocumentEntry
    fields = ('entry_id', 'description', 'product_code', 'unit', 'unit_price',
              'quantity', 'start_date', 'end_date')


class BillingDocumentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        # If it's an edit action, save the provider and the number. Check the
        # save() method to see their usefulness.
        instance = kwargs.get('instance')
        self.initial_number = instance.number if instance else None
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
            # old number.
            if self.initial_number and not obj.number:
                obj.number = self.initial_number

        if commit:
            obj.save()
        return obj


class InvoiceForm(BillingDocumentForm):
    class Meta:
        model = Invoice


class ProformaForm(BillingDocumentForm):
    class Meta:
        model = Proforma


class BillingDocumentAdmin(admin.ModelAdmin):
    list_display = ['id', 'number', 'customer_display', 'provider_display', 'state',
                    'issue_date', 'due_date', 'paid_date', 'cancel_date',
                    'sales_tax_name', 'sales_tax_percent', 'currency']
    list_display_links = list_display

    common_fields = ['company', 'email', 'address_1', 'address_2', 'city',
                     'country', 'zip_code', 'name', 'state']
    customer_search_fields = ['customer__{field}'.format(field=field)
                              for field in common_fields]
    provider_search_fields = ['provider__{field}'.format(field=field)
                              for field in common_fields]
    search_fields = customer_search_fields + provider_search_fields

    fields = (('series', 'number'), 'provider', 'customer',
              'issue_date', 'due_date', 'paid_date', 'cancel_date',
              'sales_tax_name', 'sales_tax_percent', 'currency', 'state',
              'total')
    readonly_fields = ('series', 'state', 'total')
    inlines = [DocumentEntryInline]
    actions = ['issue', 'pay', 'cancel']

    @property
    def _model(self):
        raise NotImplementedError

    def perform_action(self, request, queryset, action):
        method = getattr(self._model, action, None)
        if not method:
            self.message_user(request, 'Illegal action.', level=messages.ERROR)
            return

        exist_failed_changes = False
        failed_changes = []
        for entry in queryset:
            try:
                method(entry)
                entry.save()
            except TransitionNotAllowed:
                exist_failed_changes = True
                failed_changes.append(entry.number)

        if exist_failed_changes:
            failed_ids = ' '.join(map(str, failed_changes))
            msg = "The state change failed for invoice(s) with "\
                  "numbers: %s" % failed_ids
            self.message_user(request, msg, level=messages.ERROR)
        else:
            qs_count = queryset.count()
            msg = 'Successfully changed %d invoice(s).' % qs_count
            self.message_user(request, msg)

    def total(self, obj):
        return '{value} {currency}'.format(value=str(obj.total),
                                           currency=obj.currency)


class InvoiceAdmin(BillingDocumentAdmin):
    form = InvoiceForm
    list_display = BillingDocumentAdmin.list_display
    list_display_links = BillingDocumentAdmin.list_display_links
    search_fields = BillingDocumentAdmin.search_fields
    fields = BillingDocumentAdmin.fields + ('proforma', )
    readonly_fields = BillingDocumentAdmin.readonly_fields + ('proforma', )
    inlines = BillingDocumentAdmin.inlines
    actions = BillingDocumentAdmin.actions

    def issue(self, request, queryset):
        self.perform_action(request, queryset, 'issue')
    issue.short_description = 'Issue the selected invoices'

    def pay(self, request, queryset):
        self.perform_action(request, queryset, 'pay')
    pay.short_description = 'Pay the selected invoices'

    def cancel(self, request, queryset):
        self.perform_action(request, queryset, 'cancel')
    cancel.short_description = 'Cancel the selected invoices'


    @property
    def _model(self):
        return Invoice


class ProformaAdmin(BillingDocumentAdmin):
    form = ProformaForm
    list_display = BillingDocumentAdmin.list_display
    list_display_links = BillingDocumentAdmin.list_display_links
    search_fields = BillingDocumentAdmin.search_fields
    fields = BillingDocumentAdmin.fields + ('invoice', )
    readonly_fields = BillingDocumentAdmin.readonly_fields + ('invoice',)
    inlines = BillingDocumentAdmin.inlines
    actions = BillingDocumentAdmin.actions

    def issue(self, request, queryset):
        self.perform_action(request, queryset, 'issue')
    issue.short_description = 'Issue the selected proformas'

    def pay(self, request, queryset):
        self.perform_action(request, queryset, 'pay')
    pay.short_description = 'Pay the selected proformas'

    def cancel(self, request, queryset):
        self.perform_action(request, queryset, 'cancel')
    cancel.short_description = 'Cancel the selected proformas'

    @property
    def _model(self):
        return Proforma


admin.site.register(Plan, PlanAdmin)
admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(Customer, CustomerAdmin)
admin.site.register(Provider, ProviderAdmin)
admin.site.register(Invoice, InvoiceAdmin)
admin.site.register(Proforma, ProformaAdmin)
admin.site.register(ProductCode)
admin.site.register(MeteredFeature)
