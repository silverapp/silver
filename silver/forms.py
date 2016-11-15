from django.forms import Form
from django.template.loader import select_template


class GenericTransactionForm(Form):
    def __init__(self, payment_method, payment, request=None, *args, **kwargs):
        self.payment_method = payment_method
        self.payment = payment
        self.request = request

        super(GenericTransactionForm, self).__init__(*args, **kwargs)

    def render(self):
        template = select_template([
            'forms/{}/transaction_form.html'.format(
                self.payment_method.payment_processor.name.lower()
            ),
            'forms/transaction_form.html'
        ])

        return template.render(context={
            'payment_method': self.payment_method,
            'payment': self.payment,
            'form': self
        }, request=self.request)
