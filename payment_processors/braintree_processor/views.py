from django_fsm import TransitionNotAllowed
from django.http import HttpResponse, HttpResponseBadRequest

from silver.views import GenericTransactionView


class BraintreeTransactionView(GenericTransactionView):
    def post(self, request, transaction):
        payment_method_nonce = request.POST.get('payment_method_nonce')
        if not payment_method_nonce:
            message = 'The payment method nonce was not provided.'
            return HttpResponseBadRequest(message)

        payment_method = transaction.payment_method
        if payment_method.nonce:
            message = 'The payment method already has a payment method nonce.'
            return HttpResponseBadRequest(message)

        # initialize the payment method
        initial_data = {
            'nonce': payment_method_nonce,
            'is_recurring': request.POST.get('is_recurring', False),
            'billing_details': {
                'cardholder_name': request.POST.get('cardholder_name'),
                'postal_code': request.POST.get('postal_code')
            }
        }

        try:
            payment_method.initialize_unverified(initial_data)
            payment_method.save()
        except TransitionNotAllowed as e:
            # TODO handle this
            return HttpResponse('Something went wrong!')

        # manage the transaction
        payment_processor = payment_method.payment_processor

        if not payment_processor.execute_transaction(transaction):
            return HttpResponse('Something went wrong!')

        return HttpResponse('All is well!')
