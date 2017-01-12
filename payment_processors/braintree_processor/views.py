# Copyright (c) 2017 Presslabs SRL
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

from django_fsm import TransitionNotAllowed
from django.http import HttpResponse, HttpResponseBadRequest

from silver.views import GenericTransactionView


class BraintreeTransactionView(GenericTransactionView):
    def render_template(self):
        client_token = self.transaction.payment_processor.client_token(
            self.transaction.customer
        )

        context = {
            'payment_method': self.transaction.payment_method,
            'transaction': self.transaction,
            'document': self.transaction.document,
            'customer': self.transaction.customer,
            'provider': self.transaction.provider,
            'entries': list(self.transaction.document._entries),
            'form': self.form,
            'client_token': client_token
        }

        return self.template.render(context=context)

    def post(self, request):
        payment_method_nonce = request.POST.get('payment_method_nonce')
        if not payment_method_nonce:
            message = 'The payment method nonce was not provided.'
            return HttpResponseBadRequest(message)

        payment_method = self.transaction.payment_method
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

        if not payment_processor.execute_transaction(self.transaction):
            return HttpResponse('Something went wrong!')

        return HttpResponse('All is well!')
