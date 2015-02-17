"""URLs for the silver app."""

from django.conf.urls import patterns, include, url
from django.contrib import admin

from silver import views

admin.autodiscover()

urlpatterns = patterns(
    '',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^api-auth/', include('rest_framework.urls',
                               namespace='rest_framework')),
    url(r'', include('silver.api.urls')),

    url(r'^rendered-invoices/(?P<invoice_id>.*)/$',
        views.invoice_pdf, name='invoice-pdf'),
    url(r'^rendered-proformas/(?P<proforma_id>.*)/$',
        views.proforma_pdf, name='proforma-pdf')
)
