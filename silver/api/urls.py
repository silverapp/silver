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


from django.conf.urls import url

from silver import views as silver_views
from silver.api import views

urlpatterns = [
    url(r'^customers/$',
        views.CustomerList.as_view(), name='customer-list'),
    url(r'^customers/(?P<customer_pk>[0-9]+)/$',
        views.CustomerDetail.as_view(), name='customer-detail'),

    url(r'^customers/(?P<customer_pk>[0-9]+)/subscriptions/$',
        views.SubscriptionList.as_view(), name='subscription-list'),
    url(r'^customers/(?P<customer_pk>[0-9]+)/subscriptions/(?P<subscription_pk>[0-9]+)/$',
        views.SubscriptionDetail.as_view(), name='subscription-detail'),
    url(r'^customers/(?P<customer_pk>[0-9]+)/subscriptions/(?P<subscription_pk>[0-9]+)/metered-features/(?P<mf_product_code>([^/])+)/$',
        views.MeteredFeatureUnitsLogDetail.as_view(), name='mf-log-units'),
    url(r'^customers/(?P<customer_pk>[0-9]+)/subscriptions/(?P<subscription_pk>[0-9]+)/activate/$',
        views.SubscriptionActivate.as_view(), name='sub-activate'),
    url(r'^customers/(?P<customer_pk>[0-9]+)/subscriptions/(?P<subscription_pk>[0-9]+)/cancel/$',
        views.SubscriptionCancel.as_view(), name='sub-cancel'),
    url(r'^customers/(?P<customer_pk>[0-9]+)/subscriptions/(?P<subscription_pk>[0-9]+)/reactivate/$',
        views.SubscriptionReactivate.as_view(), name='sub-reactivate'),

    url(r'^customers/(?P<customer_pk>[0-9]+)/payment_methods/$',
        views.PaymentMethodList.as_view(), name='payment-method-list'),
    url(r'^customers/(?P<customer_pk>[0-9]+)/payment_methods/(?P<payment_method_id>[0-9]+)/$',
        views.PaymentMethodDetail.as_view(), name='payment-method-detail'),
    url(r'^customers/(?P<customer_pk>[0-9]+)/payment_methods/(?P<payment_method_id>[0-9]+)/(?P<requested_action>(cancel))_request/$',
        views.PaymentMethodAction.as_view(), name='payment-method-action'),

    url(r'^customers/(?P<customer_pk>[0-9]+)/payment_methods/(?P<payment_method_id>[0-9]+)/transactions/$',
        views.TransactionList.as_view(), name='payment-method-transaction-list'),
    url(r'^customers/(?P<customer_pk>[0-9]+)/transactions/$',
        views.TransactionList.as_view(), name='transaction-list'),
    url(r'^customers/(?P<customer_pk>[0-9]+)/transactions/(?P<transaction_uuid>[0-9a-z-]+)/$',
        views.TransactionDetail.as_view(), name='transaction-detail'),
    url(r'^customers/(?P<customer_pk>[0-9]+)/transactions/(?P<transaction_uuid>[0-9a-z-]+)/(?P<requested_action>(cancel))_request/$',
        views.TransactionAction.as_view(), name='transaction-action'),

    url(r'^payment_processors/$',
        views.PaymentProcessorList.as_view(), name='payment-processor-list'),
    url(r'^payment_processors/(?P<processor_name>[a-zA-Z\-\_]+)/$',
        views.PaymentProcessorDetail.as_view(), name='payment-processor-detail'),

    url(r'^plans/$',
        views.PlanList.as_view(), name='plan-list'),
    url(r'^plans/(?P<pk>[0-9]+)/$',
        views.PlanDetail.as_view(), name='plan-detail'),
    url(r'plans/(?P<pk>[0-9]+)/metered-features/$',
        views.PlanMeteredFeatures.as_view(), name='plans-metered-features'),

    url(r'^metered-features/$',
        views.MeteredFeatureList.as_view(), name='metered-feature-list'),

    url(r'^providers/$',
        views.ProviderListCreate.as_view(), name='provider-list'),
    url(r'^providers/(?P<pk>[0-9]+)/$',
        views.ProviderRetrieveUpdateDestroy.as_view(), name='provider-detail'),

    url(r'^product-codes/$',
        views.ProductCodeListCreate.as_view(), name='productcode-list'),
    url(r'^product-codes/(?P<pk>[0-9]+)/$',
        views.ProductCodeRetrieveUpdate.as_view(), name='productcode-detail'),

    url(r'^invoices/$',
        views.InvoiceListCreate.as_view(), name='invoice-list'),
    url(r'^invoices/(?P<pk>[0-9]+)/$',
        views.InvoiceRetrieveUpdate.as_view(), name='invoice-detail'),
    url(r'^invoices/(?P<document_pk>[0-9]+)/entries/$',
        views.InvoiceEntryCreate.as_view(), name='invoice-entry-create'),
    url(r'^invoices/(?P<document_pk>[0-9]+)/entries/(?P<entry_pk>[0-9]+)/$',
        views.InvoiceEntryUpdateDestroy.as_view(), name='invoice-entry-update'),
    url(r'^invoices/(?P<pk>[0-9]+)/state/$',
        views.InvoiceStateHandler.as_view(), name='invoice-state'),
    url(r'^invoices/(?P<invoice_id>\d+).pdf$',
        silver_views.invoice_pdf, name='invoice-pdf'),

    url(r'^proformas/$',
        views.ProformaListCreate.as_view(), name='proforma-list'),
    url(r'^proformas/(?P<pk>[0-9]+)/$',
        views.ProformaRetrieveUpdate.as_view(), name='proforma-detail'),
    url(r'^proformas/(?P<document_pk>[0-9]+)/entries/$',
        views.ProformaEntryCreate.as_view(), name='proforma-entry-create'),
    url(r'^proformas/(?P<document_pk>[0-9]+)/entries/(?P<entry_pk>[0-9]+)/$',
        views.ProformaEntryUpdateDestroy.as_view(),
        name='proforma-entry-update'),
    url(r'^proformas/(?P<pk>[0-9]+)/state/$',
        views.ProformaStateHandler.as_view(), name='proforma-state'),
    url(r'^proformas/(?P<pk>[0-9]+)/invoice/$',
        views.ProformaInvoiceRetrieveCreate.as_view(),
        name='proforma-invoice'),
    url(r'^proformas/(?P<proforma_id>\d+).pdf$',
        silver_views.proforma_pdf, name='proforma-pdf'),

    url(r'^documents/$',
        views.DocumentList.as_view(), name='document-list')
]
