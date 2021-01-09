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

from django.conf.urls import re_path

from silver import views as silver_views
from silver.api.views import billing_entities_views, documents_views, payment_method_views, \
    plan_views, product_code_views, subscription_views, transaction_views


urlpatterns = [
    re_path(r'^customers/$',
            billing_entities_views.CustomerList.as_view(), name='customer-list'),
    re_path(r'^customers/(?P<customer_pk>[0-9]+)/$',
            billing_entities_views.CustomerDetail.as_view(), name='customer-detail'),

    re_path(r'^customers/(?P<customer_pk>[0-9]+)/subscriptions/$',
            subscription_views.SubscriptionList.as_view(), name='subscription-list'),
    re_path(r'^customers/(?P<customer_pk>[0-9]+)/subscriptions/(?P<subscription_pk>[0-9]+)/$',
            subscription_views.SubscriptionDetail.as_view(), name='subscription-detail'),
    re_path(r'^customers/(?P<customer_pk>[0-9]+)/subscriptions/(?P<subscription_pk>[0-9]+)/metered-features/(?P<mf_product_code>([^/])+)/$',
            subscription_views.MeteredFeatureUnitsLogDetail.as_view(), name='mf-log-units'),
    re_path(r'^customers/(?P<customer_pk>[0-9]+)/subscriptions/(?P<subscription_pk>[0-9]+)/activate/$',
            subscription_views.SubscriptionActivate.as_view(), name='sub-activate'),
    re_path(r'^customers/(?P<customer_pk>[0-9]+)/subscriptions/(?P<subscription_pk>[0-9]+)/cancel/$',
            subscription_views.SubscriptionCancel.as_view(), name='sub-cancel'),
    re_path(r'^customers/(?P<customer_pk>[0-9]+)/subscriptions/(?P<subscription_pk>[0-9]+)/reactivate/$',
            subscription_views.SubscriptionReactivate.as_view(), name='sub-reactivate'),

    re_path(r'^customers/(?P<customer_pk>[0-9]+)/payment_methods/$',
            payment_method_views.PaymentMethodList.as_view(), name='payment-method-list'),
    re_path(r'^customers/(?P<customer_pk>[0-9]+)/payment_methods/(?P<payment_method_id>[0-9]+)/$',
            payment_method_views.PaymentMethodDetail.as_view(), name='payment-method-detail'),
    re_path(r'^customers/(?P<customer_pk>[0-9]+)/payment_methods/(?P<payment_method_id>[0-9]+)/(?P<requested_action>(cancel))_request/$',
            payment_method_views.PaymentMethodAction.as_view(), name='payment-method-action'),

    re_path(r'^customers/(?P<customer_pk>[0-9]+)/payment_methods/(?P<payment_method_id>[0-9]+)/transactions/$',
            transaction_views.TransactionList.as_view(), name='payment-method-transaction-list'),
    re_path(r'^customers/(?P<customer_pk>[0-9]+)/transactions/$',
            transaction_views.TransactionList.as_view(), name='transaction-list'),
    re_path(r'^customers/(?P<customer_pk>[0-9]+)/transactions/(?P<transaction_uuid>[0-9a-z-]+)/$',
            transaction_views.TransactionDetail.as_view(), name='transaction-detail'),
    re_path(r'^customers/(?P<customer_pk>[0-9]+)/transactions/(?P<transaction_uuid>[0-9a-z-]+)/(?P<requested_action>(cancel))_request/$',
            transaction_views.TransactionAction.as_view(), name='transaction-action'),

    re_path(r'^payment_processors/$',
            payment_method_views.PaymentProcessorList.as_view(), name='payment-processor-list'),
    re_path(r'^payment_processors/(?P<processor_name>[a-zA-Z\-\_]+)/$',
            payment_method_views.PaymentProcessorDetail.as_view(), name='payment-processor-detail'),

    re_path(r'^plans/$',
            plan_views.PlanList.as_view(), name='plan-list'),
    re_path(r'^plans/(?P<pk>[0-9]+)/$',
            plan_views.PlanDetail.as_view(), name='plan-detail'),
    re_path(r'plans/(?P<pk>[0-9]+)/metered-features/$',
            plan_views.PlanMeteredFeatures.as_view(), name='plans-metered-features'),

    re_path(r'^metered-features/$',
            subscription_views.MeteredFeatureList.as_view(), name='metered-feature-list'),

    re_path(r'^providers/$',
            billing_entities_views.ProviderListCreate.as_view(), name='provider-list'),
    re_path(r'^providers/(?P<pk>[0-9]+)/$',
            billing_entities_views.ProviderRetrieveUpdateDestroy.as_view(), name='provider-detail'),

    re_path(r'^product-codes/$',
            product_code_views.ProductCodeListCreate.as_view(), name='productcode-list'),
    re_path(r'^product-codes/(?P<pk>[0-9]+)/$',
            product_code_views.ProductCodeRetrieveUpdate.as_view(), name='productcode-detail'),

    re_path(r'^invoices/$',
            documents_views.InvoiceListCreate.as_view(), name='invoice-list'),
    re_path(r'^invoices/(?P<pk>[0-9]+)/$',
            documents_views.InvoiceRetrieveUpdate.as_view(), name='invoice-detail'),
    re_path(r'^invoices/(?P<document_pk>[0-9]+)/entries/$',
            documents_views.InvoiceEntryCreate.as_view(), name='invoice-entry-create'),
    re_path(r'^invoices/(?P<document_pk>[0-9]+)/entries/(?P<entry_pk>[0-9]+)/$',
            documents_views.InvoiceEntryUpdateDestroy.as_view(), name='invoice-entry-update'),
    re_path(r'^invoices/(?P<pk>[0-9]+)/state/$',
            documents_views.InvoiceStateHandler.as_view(), name='invoice-state'),
    re_path(r'^invoices/(?P<invoice_id>\d+).pdf$',
            silver_views.invoice_pdf, name='invoice-pdf'),

    re_path(r'^proformas/$',
            documents_views.ProformaListCreate.as_view(), name='proforma-list'),
    re_path(r'^proformas/(?P<pk>[0-9]+)/$',
            documents_views.ProformaRetrieveUpdate.as_view(), name='proforma-detail'),
    re_path(r'^proformas/(?P<document_pk>[0-9]+)/entries/$',
            documents_views.ProformaEntryCreate.as_view(), name='proforma-entry-create'),
    re_path(r'^proformas/(?P<document_pk>[0-9]+)/entries/(?P<entry_pk>[0-9]+)/$',
            documents_views.ProformaEntryUpdateDestroy.as_view(),
            name='proforma-entry-update'),
    re_path(r'^proformas/(?P<pk>[0-9]+)/state/$',
            documents_views.ProformaStateHandler.as_view(), name='proforma-state'),
    re_path(r'^proformas/(?P<pk>[0-9]+)/invoice/$',
            documents_views.ProformaInvoiceRetrieveCreate.as_view(),
            name='proforma-invoice'),
    re_path(r'^proformas/(?P<proforma_id>\d+).pdf$',
            silver_views.proforma_pdf, name='proforma-pdf'),
    re_path(r'^pdfs/(?P<pdf_pk>[0-9]+)/$',
            documents_views.PDFRetrieve.as_view(),
            name='pdf'),
    re_path(r'^documents/$',
            documents_views.DocumentList.as_view(), name='document-list')
]
