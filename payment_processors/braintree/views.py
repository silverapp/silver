from django.http import HttpResponse, HttpResponseBadRequest

from silver.views import GenericTransactionView


class BraintreeTransactionView(GenericTransactionView):
    def post(self, request, transaction):
        if not request.POST.get('payment_method_nonce'):
            return HttpResponseBadRequest()

        payment_processor = transaction.payment_method.payment_processor
        payment_processor.manage_transaction(transaction)

        return HttpResponse('All is well!')
