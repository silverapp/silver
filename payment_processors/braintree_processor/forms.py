from django import forms

from silver.forms import GenericTransactionForm


class BraintreeTransactionForm(GenericTransactionForm):

    def get_context(self):
        context = super(BraintreeTransactionForm, self).get_context()
        context['client_token'] = self.transaction.payment_method.client_token

        return context
