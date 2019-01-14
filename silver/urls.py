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


"""URLs for the silver app."""

from __future__ import absolute_import

from django.conf.urls import include, url
from django.contrib import admin

from silver.views import (pay_transaction_view, complete_payment_view,
                          InvoiceAutocomplete, ProformaAutocomplete,
                          PaymentMethodAutocomplete)


admin.autodiscover()


urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^api-auth/', include('rest_framework.urls',
                               namespace='rest_framework')),
    url(r'', include('silver.api.urls')),

    url(r'pay/(?P<token>[0-9a-zA-Z-_\.]+)/$',
        pay_transaction_view, name='payment'),
    url(r'pay/(?P<token>[0-9a-zA-Z-_\.]+)/complete$',
        complete_payment_view, name='payment-complete'),

    url(r'^autocomplete/invoices/$',
        InvoiceAutocomplete.as_view(), name='autocomplete-invoice'),
    url(r'^autocomplete/proformas/$',
        ProformaAutocomplete.as_view(), name='autocomplete-proforma'),
    url(r'^autocomplete/payment-method/$',
        PaymentMethodAutocomplete.as_view(), name='autocomplete-payment-method'),
]
