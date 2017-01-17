# Copyright (c) 2016 Presslabs SRL
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
from uuid import UUID

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
from django.http import HttpResponseGone
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from dal import autocomplete
from rest_framework.exceptions import MethodNotAllowed

from silver.models.documents import Proforma, Invoice
from silver.models.transactions import Transaction


@login_required
def proforma_pdf(request, proforma_id):
    proforma = get_object_or_404(Proforma, id=proforma_id)
    return HttpResponseRedirect(proforma.pdf.url)


@login_required
def invoice_pdf(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    return HttpResponseRedirect(invoice.pdf.url)


@csrf_exempt
def initialize_transaction(request, transaction_uuid):
    try:
        uuid = UUID(transaction_uuid, version=4)
    except ValueError:
        raise Http404

    transaction = get_object_or_404(Transaction, uuid=uuid)

    transaction.last_access = timezone.now()
    transaction.save()

    if transaction.payment_processor.was_transaction_initialized(transaction,
                                                                 request):
        return HttpResponseRedirect(transaction.success_url)

    return HttpResponseRedirect(transaction.failed_url)



@csrf_exempt
def pay_transaction_view(request, transaction_uuid):
    try:
        uuid = UUID(transaction_uuid, version=4)
    except ValueError:
        raise Http404

    transaction = get_object_or_404(Transaction, uuid=uuid)

    view = transaction.payment_processor.get_view(transaction, request)
    if not view:
        raise Http404

    if not transaction.can_be_consumed:
        return HttpResponseGone("The transaction is no longer available.")

    transaction.last_access = timezone.now()
    transaction.save()

    try:
        return view(request)
    except NotImplementedError:
        raise Http404


class GenericTransactionView(View):
    form = None
    template = None
    transaction = None

    def get_context_data(self):
        return {
            'payment_method': self.transaction.payment_method,
            'transaction': self.transaction,
            'document': self.transaction.document,
            'customer': self.transaction.customer,
            'provider': self.transaction.provider,
            'entries': list(self.transaction.document._entries),
            'form': self.form
        }

    def render_template(self):
        return self.template.render(context=self.get_context_data())

    def get(self, request):
        return HttpResponse(self.render_template())

    def post(self, request):
        raise MethodNotAllowed


class DocumentAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not (self.request.user.is_authenticated() and self.request.user.is_staff):
            raise Http404

        queryset = self.model.objects.all()

        if self.q:
            q = self.q.rsplit('-')
            if len(q) == 2:
                query = (Q(series=q[0]), Q(number=q[1]))
            else:
                query = (Q(series__istartswith=self.q) |
                         Q(number__istartswith=self.q))
            queryset = queryset.filter(query)

        return queryset


class InvoiceAutocomplete(DocumentAutocomplete):
    def __init__(self, **kwargs):
        self.model = Invoice

        super(InvoiceAutocomplete, self).__init__(**kwargs)


class ProformaAutocomplete(DocumentAutocomplete):
    def __init__(self, **kwargs):
        self.model = Invoice

        super(ProformaAutocomplete, self).__init__(**kwargs)
