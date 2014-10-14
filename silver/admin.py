"""Admin classes for the silver app."""
from django.contrib import admin
from models import Plan, MeteredFeature, Subscription, BillingDetail, Customer


class PlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'interval', 'interval_count', 'amount', 'currency',
                    'trial_period_days', 'due_days', 'generate_after', ]
    search_fields = ['due_days', 'name', ]


class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['customer', 'plan', 'trial_end', 'start_date', 'ended_at',
                    'state', ]
    list_filter = ['plan', 'state']
    readonly_fields = ['state', ]
    actions = ['activate', 'cancel', 'end', ]

    def activate(modeladmin, request, queryset):
        for entry in queryset:
            entry.activate()
            entry.save()

    def cancel(modeladmin, request, queryset):
        for entry in queryset:
            entry.cancel()
            entry.save()

    def end(modeladmin, request, queryset):
        for entry in queryset:
            entry.end()
            entry.save()


class CustomerAdmin(admin.ModelAdmin):
    list_display = ['customer_reference', 'billing_details',
                    'sales_tax_percent', 'sales_tax_name',
                    'consolidated_billing', ]


class BillingDetailAdmin(admin.ModelAdmin):
    def get_model_perms(self, request):
        # hide this from the admin interface
        return {}


class MeteredFeatureAdmin(admin.ModelAdmin):
    def get_model_perms(self, request):
        return {}


admin.site.register(Plan, PlanAdmin)
admin.site.register(MeteredFeature, MeteredFeatureAdmin)
admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(Customer, CustomerAdmin)
admin.site.register(BillingDetail, BillingDetailAdmin)
