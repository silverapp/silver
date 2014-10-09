"""Admin classes for the silver app."""
from django.contrib import admin
from models import Plan, MeteredFeature, Subscription, Customer


class PlanAdmin(admin.ModelAdmin):
    list_display = ['interval', 'interval_count', 'amount', 'currency', 'name',
                    'trial_period_days', 'metered_features', 'due_days',
                    'generate_after', ]
    search_fields = ['due_days', 'name', ]


class MeteredFeatureAdmin(admin.ModelAdmin):
    list_display = ['name', 'price_per_unit', 'included_units', ]


class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['plan', 'customer', 'trial_end', 'start_date', 'ended_at',
                    'state', ]


class CustomerAdmin(admin.ModelAdmin):
    list_display = ['customer_reference', 'billing_details',
                    'sales_tax_percent', 'sales_tax_name',
                    'consolidated_billing', ]


admin.site.register(Plan, PlanAdmin)
admin.site.register(MeteredFeature, MeteredFeatureAdmin)
admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(Customer, CustomerAdmin)