from django.forms import Form
from django.template.loader import get_template


class GenericPaymentForm(Form):
    def __init__(self, payment_method, payment, request=None, *args, **kwargs):
        self.payment_method = payment_method
        self.payment = payment
        self.request = request

        super(GenericPaymentForm, self).__init__(*args, **kwargs)

    def render(self):
        template = get_template('forms/base_form.html')

        return template.render(context={
            'payment_method': self.payment_method,
            'payment': self.payment,
            'form': self
        }, request=self.request)
