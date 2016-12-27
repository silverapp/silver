from django.forms import Form
from django.template.loader import select_template


class GenericTransactionForm(Form):
    def __init__(self, payment_method, transaction, request=None, *args, **kwargs):
        self.payment_method = payment_method
        self.transaction = transaction
        self.request = request

        super(GenericTransactionForm, self).__init__(*args, **kwargs)

    def get_context(self):
        return {
            'payment_method': self.payment_method,
            'transaction': self.transaction,
            'document': self.transaction.document,
            'customer': self.transaction.customer,
            'provider': self.transaction.provider,
            'entries': list(self.transaction.document._entries),
            'form': self
        }

    def render(self):
        template = select_template([
            'forms/{}/transaction_form.html'.format(
                self.payment_method.processor.reference
            ),
            'forms/transaction_form.html'
        ])

        return template.render(context=self.get_context())
