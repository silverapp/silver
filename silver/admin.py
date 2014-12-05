from django import forms
from django.contrib import admin, messages
from django_fsm import TransitionNotAllowed

from models import (Plan, MeteredFeature, Subscription, Customer, Provider,
                    MeteredFeatureUnitsLog, Invoice, InvoiceEntry)


class PlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'interval', 'interval_count', 'amount', 'currency',
                    'trial_period_days', 'due_days', 'generate_after',
                    'enabled', 'private']
    search_fields = ['due_days', 'name']


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


class CustomerAdmin(admin.ModelAdmin):
    list_display = ['name', 'company', 'customer_reference', 'email',
                    'complete_address', 'sales_tax_percent', 'sales_tax_name',
                    'consolidated_billing']
    list_display_links = list_display
    search_fields = ['customer_reference', 'name', 'company', 'address_1',
                     'address_2', 'city', 'zip_code', 'country', 'state',
                     'email']
    exclude = ['live']


class MeteredFeatureAdmin(admin.ModelAdmin):
    def get_model_perms(self, request):
        return {}


class ProviderAdmin(admin.ModelAdmin):
    list_display = ['name', 'company', 'email', 'address_1', 'address_2',
                    'city', 'state', 'zip_code', 'country']
    list_display_links = list_display
    search_fields = list_display
    exclude = ['live']


class InvoiceEntryInline(admin.TabularInline):
    model = InvoiceEntry


class InvoiceForm(forms.ModelForm):
    invoice_customer = forms.ModelChoiceField(queryset=Customer.objects.all(),
                                              label='Customer')
    invoice_provider = forms.ModelChoiceField(queryset=Provider.objects.all(),
                                              label='Provider')

    class Meta:
        model = Invoice
        fields = ('invoice_provider', 'invoice_customer', 'issue_date',
                  'due_date', 'paid_date', 'cancel_date', 'sales_tax_name',
                  'sales_tax_percent', 'currency', 'state')

    def __init__(self, *args, **kwargs):
        super(InvoiceForm, self).__init__(*args, **kwargs)
        instance = kwargs.get('instance')
        if instance:
            customer_id = instance.customer.customer_ref.id
            if customer_id:
                self.fields['invoice_customer'].initial = customer_id

            provider_id = instance.provider.provider_ref.id
            if provider_id:
                self.fields['invoice_provider'].initial = provider_id


class InvoiceAdmin(admin.ModelAdmin):
    form = InvoiceForm
    list_display = ['customer_display', 'provider_display', 'state', 'due_date',
                    'paid_date', 'cancel_date', 'sales_tax_name',
                    'sales_tax_percent', 'currency']
    list_display_links = list_display

    common_fields = ['company', 'email', 'address_1', 'address_2', 'city',
                     'country', 'zip_code', 'name', 'state']
    customer_search_fields = ['customer__{field}'.format(field=field)
                              for field in common_fields]
    provider_search_fields = ['provider__{field}'.format(field=field)
                              for field in common_fields]
    search_fields = customer_search_fields + provider_search_fields
    inlines = [InvoiceEntryInline]

    def save_model(self, request, obj, form, change):
        customer_id = request.POST.get('invoice_customer') or -1
        provider_id = request.POST.get('invoice_provider') or -1
        obj.save(invoice_customer_id=customer_id,
                 invoice_provider_id=provider_id)


admin.site.register(Plan, PlanAdmin)
admin.site.register(MeteredFeature, MeteredFeatureAdmin)
admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(Customer, CustomerAdmin)
admin.site.register(Provider, ProviderAdmin)
admin.site.register(Invoice, InvoiceAdmin)
