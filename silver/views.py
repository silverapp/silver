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
from furl import furl
from dal import autocomplete

from django.db.models import Q
from django.utils import timezone
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import Http404, HttpResponseRedirect


from silver.models.payment_methods import PaymentMethod
from silver.models.transactions import Transaction
from silver.models.documents import Proforma, Invoice
from silver.models.transactions.codes import FAIL_CODES
from silver.payment_processors import get_instance
from silver.utils.decorators import get_transaction_from_token


@login_required
def proforma_pdf(request, proforma_id):
    proforma = get_object_or_404(Proforma, id=proforma_id)
    return HttpResponseRedirect(proforma.pdf.url)


@login_required
def invoice_pdf(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    return HttpResponseRedirect(invoice.pdf.url)


@csrf_exempt
@get_transaction_from_token
def complete_payment_view(request, transaction, expired=None):
    if transaction.state == transaction.States.Initial:
        payment_processor = get_instance(transaction.payment_processor)
        payment_processor.handle_transaction_response(transaction, request)

    if 'return_url' in request.GET:
        redirect_url = furl(request.GET['return_url']).add({
                                'transaction_uuid': transaction.uuid
                            }).url
        return HttpResponseRedirect(redirect_url)
    else:
        return render(request, 'transactions/complete_payment.html',
                      {
                          'transaction': transaction,
                          'document': transaction.document,
                          'fail_data': FAIL_CODES.get(transaction.fail_code),
                      })


@csrf_exempt
@get_transaction_from_token
def pay_transaction_view(request, transaction, expired=None):
    if expired:
        return render(request, 'transactions/expired_payment.html',
                      {
                          'document': transaction.document,
                      })

    if transaction.state != Transaction.States.Initial:
        return render(request, 'transactions/complete_payment.html',
                      {
                          'transaction': transaction,
                          'document': transaction.document,
                          'fail_data': FAIL_CODES.get(transaction.fail_code)
                      })

    payment_processor = transaction.payment_method.get_payment_processor()

    view = payment_processor.get_view(transaction, request)
    if not view or not transaction.can_be_consumed:
        return render(request, 'transactions/expired_payment.html',
                      {
                          'document': transaction.document,
                      })

    transaction.last_access = timezone.now()
    transaction.save()

    try:
        return view(request)
    except NotImplementedError:
        raise Http404


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
                         Q(number__istartswith=self.q) |
                         Q(customer__first_name__icontains=self.q) |
                         Q(customer__last_name__icontains=self.q) |
                         Q(customer__company__icontains=self.q))
            queryset = queryset.filter(query)

        return queryset


class InvoiceAutocomplete(DocumentAutocomplete):
    def __init__(self, **kwargs):
        self.model = Invoice

        super(InvoiceAutocomplete, self).__init__(**kwargs)


class ProformaAutocomplete(DocumentAutocomplete):
    def __init__(self, **kwargs):
        self.model = Proforma

        super(ProformaAutocomplete, self).__init__(**kwargs)


class PaymentMethodAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not (self.request.user.is_authenticated() and self.request.user.is_staff):
            raise Http404

        queryset = PaymentMethod.objects.all()

        if self.q:
            query = (Q(customer__first_name__istartswith=self.q) |
                     Q(customer__last_name__istartswith=self.q) |
                     Q(payment_processor__istartswith=self.q) |
                     Q(display_info__istartswith=self.q))
            queryset = queryset.filter(query)

        return queryset
