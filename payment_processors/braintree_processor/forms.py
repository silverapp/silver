from django import forms
from silver.forms import GenericTransactionForm


class BraintreeTransactionForm(GenericTransactionForm):
    card_number = forms.CharField(
        label='Card number', required=True,
        widget=forms.TextInput(attrs={
            "id": "id-card-number", "data-braintree-name": "number"
        })
    )
    exp_date = forms.DateField(
        label='Expiration (mm/yy)',
        input_formats=['%m/%y', ], required=True,
        widget=forms.DateInput(attrs={
            "id": "id-exp-date", "data-braintree-name": "expiration_date"
        })
    )
    cvv = forms.IntegerField(
        label='CVV', max_value=9999, min_value=0, required=True,
        widget=forms.TextInput(attrs={
            "id": "id-cvv", "data-braintree-name": "cvv"
        })
    )
    cardholder_name = forms.CharField(
        label='Name on card', required=True,
        widget=forms.TextInput(attrs={"id": "id-cardholder-name"})
    )
    postal_code = forms.CharField(
        label='Postal code', required=True,
        widget=forms.TextInput(attrs={"id": "id-postal-code"})
    )

    def get_context(self):
        context = super(BraintreeTransactionForm, self).get_context()
        context['client_token'] = self.transaction.payment_method.client_token
        print context['client_token'], 'client_token'
        return context
