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
from django.http import HttpResponse
from django.http import HttpResponseGone
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from silver.models.documents import Proforma, Invoice
from silver.models.transactions import Transaction
from silver.forms import GenericTransactionForm


@login_required
def proforma_pdf(request, proforma_id):
    proforma = get_object_or_404(Proforma, id=proforma_id)
    return HttpResponseRedirect(proforma.pdf.url)


@login_required
def invoice_pdf(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    return HttpResponseRedirect(invoice.pdf.url)


@csrf_exempt
def pay_transaction_view(request, transaction_uuid):
    try:
        uuid = UUID(transaction_uuid, version=4)
    except ValueError:
        raise Http404

    transaction = get_object_or_404(Transaction, uuid=uuid)

    view_class = transaction.payment_processor.view_class
    if not view_class:
        raise Http404

    if not transaction.can_be_consumed:
        return HttpResponseGone("The transaction is no longer available.")

    transaction.last_access = timezone.now()
    transaction.save()

    try:
        return view_class().handle_transaction_request(request, transaction)
    except NotImplementedError:
        raise Http404


class GenericTransactionView(object):
    form_class = GenericTransactionForm

    def render_form(self, request, transaction):
        return self.form_class(payment_method=transaction.payment_method,
                               transaction=transaction).render()

    def handle_transaction_request(self, request, transaction):
        if self.form_class:
            return HttpResponse(self.render_form(request, transaction))
        else:
            raise NotImplementedError
