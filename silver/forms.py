from django.forms import Form


class GenericTransactionForm(Form):
    def __init__(self, payment_method, transaction, request=None, *args, **kwargs):
        self.payment_method = payment_method
        self.transaction = transaction
        self.request = request

        super(GenericTransactionForm, self).__init__(*args, **kwargs)
