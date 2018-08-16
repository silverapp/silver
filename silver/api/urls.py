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

from __future__ import absolute_import

from django.conf.urls import url

from silver import views as silver_views
from silver.api.views import billing_entities_views, documents_views, payment_method_views, \
    plan_views, product_code_views, subscription_views, transaction_views


urlpatterns = [
    url(r'^customers/$',
        billing_entities_views.CustomerList.as_view(), name='customer-list'),
    url(r'^customers/(?P<customer_pk>[0-9]+)/$',
        billing_entities_views.CustomerDetail.as_view(), name='customer-detail'),

    url(r'^customers/(?P<customer_pk>[0-9]+)/subscriptions/$',
        subscription_views.SubscriptionList.as_view(), name='subscription-list'),
    url(r'^customers/(?P<customer_pk>[0-9]+)/subscriptions/(?P<subscription_pk>[0-9]+)/$',
        subscription_views.SubscriptionDetail.as_view(), name='subscription-detail'),
    url(r'^customers/(?P<customer_pk>[0-9]+)/subscriptions/(?P<subscription_pk>[0-9]+)/metered-features/(?P<mf_product_code>([^/])+)/$',
        subscription_views.MeteredFeatureUnitsLogDetail.as_view(), name='mf-log-units'),
    url(r'^customers/(?P<customer_pk>[0-9]+)/subscriptions/(?P<subscription_pk>[0-9]+)/activate/$',
        subscription_views.SubscriptionActivate.as_view(), name='sub-activate'),
    url(r'^customers/(?P<customer_pk>[0-9]+)/subscriptions/(?P<subscription_pk>[0-9]+)/cancel/$',
        subscription_views.SubscriptionCancel.as_view(), name='sub-cancel'),
    url(r'^customers/(?P<customer_pk>[0-9]+)/subscriptions/(?P<subscription_pk>[0-9]+)/reactivate/$',
        subscription_views.SubscriptionReactivate.as_view(), name='sub-reactivate'),

    url(r'^customers/(?P<customer_pk>[0-9]+)/payment_methods/$',
        payment_method_views.PaymentMethodList.as_view(), name='payment-method-list'),
    url(r'^customers/(?P<customer_pk>[0-9]+)/payment_methods/(?P<payment_method_id>[0-9]+)/$',
        payment_method_views.PaymentMethodDetail.as_view(), name='payment-method-detail'),
    url(r'^customers/(?P<customer_pk>[0-9]+)/payment_methods/(?P<payment_method_id>[0-9]+)/(?P<requested_action>(cancel))_request/$',
        payment_method_views.PaymentMethodAction.as_view(), name='payment-method-action'),

    url(r'^customers/(?P<customer_pk>[0-9]+)/payment_methods/(?P<payment_method_id>[0-9]+)/transactions/$',
        transaction_views.TransactionList.as_view(), name='payment-method-transaction-list'),
    url(r'^customers/(?P<customer_pk>[0-9]+)/transactions/$',
        transaction_views.TransactionList.as_view(), name='transaction-list'),
    url(r'^customers/(?P<customer_pk>[0-9]+)/transactions/(?P<transaction_uuid>[0-9a-z-]+)/$',
        transaction_views.TransactionDetail.as_view(), name='transaction-detail'),
    url(r'^customers/(?P<customer_pk>[0-9]+)/transactions/(?P<transaction_uuid>[0-9a-z-]+)/(?P<requested_action>(cancel))_request/$',
        transaction_views.TransactionAction.as_view(), name='transaction-action'),

    url(r'^payment_processors/$',
        payment_method_views.PaymentProcessorList.as_view(), name='payment-processor-list'),
    url(r'^payment_processors/(?P<processor_name>[a-zA-Z\-\_]+)/$',
        payment_method_views.PaymentProcessorDetail.as_view(), name='payment-processor-detail'),

    url(r'^plans/$',
        plan_views.PlanList.as_view(), name='plan-list'),
    url(r'^plans/(?P<pk>[0-9]+)/$',
        plan_views.PlanDetail.as_view(), name='plan-detail'),
    url(r'plans/(?P<pk>[0-9]+)/metered-features/$',
        plan_views.PlanMeteredFeatures.as_view(), name='plans-metered-features'),

    url(r'^metered-features/$',
        subscription_views.MeteredFeatureList.as_view(), name='metered-feature-list'),

    url(r'^providers/$',
        billing_entities_views.ProviderListCreate.as_view(), name='provider-list'),
    url(r'^providers/(?P<pk>[0-9]+)/$',
        billing_entities_views.ProviderRetrieveUpdateDestroy.as_view(), name='provider-detail'),

    url(r'^product-codes/$',
        product_code_views.ProductCodeListCreate.as_view(), name='productcode-list'),
    url(r'^product-codes/(?P<pk>[0-9]+)/$',
        product_code_views.ProductCodeRetrieveUpdate.as_view(), name='productcode-detail'),

    url(r'^invoices/$',
        documents_views.InvoiceListCreate.as_view(), name='invoice-list'),
    url(r'^invoices/(?P<pk>[0-9]+)/$',
        documents_views.InvoiceRetrieveUpdate.as_view(), name='invoice-detail'),
    url(r'^invoices/(?P<document_pk>[0-9]+)/entries/$',
        documents_views.InvoiceEntryCreate.as_view(), name='invoice-entry-create'),
    url(r'^invoices/(?P<document_pk>[0-9]+)/entries/(?P<entry_pk>[0-9]+)/$',
        documents_views.InvoiceEntryUpdateDestroy.as_view(), name='invoice-entry-update'),
    url(r'^invoices/(?P<pk>[0-9]+)/state/$',
        documents_views.InvoiceStateHandler.as_view(), name='invoice-state'),
    url(r'^invoices/(?P<invoice_id>\d+).pdf$',
        silver_views.invoice_pdf, name='invoice-pdf'),

    url(r'^proformas/$',
        documents_views.ProformaListCreate.as_view(), name='proforma-list'),
    url(r'^proformas/(?P<pk>[0-9]+)/$',
        documents_views.ProformaRetrieveUpdate.as_view(), name='proforma-detail'),
    url(r'^proformas/(?P<document_pk>[0-9]+)/entries/$',
        documents_views.ProformaEntryCreate.as_view(), name='proforma-entry-create'),
    url(r'^proformas/(?P<document_pk>[0-9]+)/entries/(?P<entry_pk>[0-9]+)/$',
        documents_views.ProformaEntryUpdateDestroy.as_view(),
        name='proforma-entry-update'),
    url(r'^proformas/(?P<pk>[0-9]+)/state/$',
        documents_views.ProformaStateHandler.as_view(), name='proforma-state'),
    url(r'^proformas/(?P<pk>[0-9]+)/invoice/$',
        documents_views.ProformaInvoiceRetrieveCreate.as_view(),
        name='proforma-invoice'),
    url(r'^proformas/(?P<proforma_id>\d+).pdf$',
        silver_views.proforma_pdf, name='proforma-pdf'),
    url(r'^pdfs/(?P<pdf_pk>[0-9]+)/$',
        documents_views.PDFRetrieve.as_view(),
        name='pdf'),
    url(r'^documents/$',
        documents_views.DocumentList.as_view(), name='document-list')
]
