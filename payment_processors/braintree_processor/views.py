from django.http import Http404

from .forms import BraintreeTransactionForm
from silver.views import GenericTransactionView


class BraintreeTransactionView(GenericTransactionView):
    form_class = BraintreeTransactionForm

    def post(self, request, transaction):
        # this should receive the payment method nonce
        raise Http404
