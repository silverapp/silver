from django.http import Http404
from silver.views import GenericTransactionView


class BraintreeTransactionView(GenericTransactionView):
    def post(self, request, transaction):
        # this should receive the payment method nonce
        raise Http404
