"""Admin classes for the silver app."""
from django.contrib import admin, messages
from django_fsm import TransitionNotAllowed

from models import (Plan, MeteredFeature, Subscription, Customer, Provider,
                    MeteredFeatureUnitsLog, Offer)

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


class OfferAdmin(admin.ModelAdmin):
    model = Offer
    list_display = ('name', 'plans_list')


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
    list_display = ['customer_reference', 'name', 'company', 'email',
                    'complete_address', 'sales_tax_percent', 'sales_tax_name',
                    'consolidated_billing']
    search_fields = ['customer_reference', 'name', 'company', 'address_1',
                     'address_2', 'city', 'zip_code', 'country', 'state',
                     'email']


class MeteredFeatureAdmin(admin.ModelAdmin):
    def get_model_perms(self, request):
        return {}


class ProviderAdmin(LiveModelAdmin):
    list_display = ['name', 'company', 'email', 'address_1', 'address_2',
                    'city', 'state', 'zip_code', 'country']
    search_fields = list_display


admin.site.register(Plan, PlanAdmin)
admin.site.register(MeteredFeature, MeteredFeatureAdmin)
admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(Customer, CustomerAdmin)
admin.site.register(Offer, OfferAdmin)
admin.site.register(Provider, ProviderAdmin)
