from django.template.loader import select_template
from django.utils.deconstruct import deconstructible


@deconstructible
class PaymentProcessorBase(object):
    form_class = None
    payment_method_class = None
    transaction_view_class = None

    def setup(self, data):
        """
            Sets up the Payment Processor
        """

        raise NotImplementedError

    def get_view(self, transaction, request, **kwargs):
        kwargs.update({
            'form': self.get_form(transaction, request),
            'template': self.get_template(transaction),
            'transaction': transaction
        })
        return self.transaction_view_class.as_view(**kwargs)

    def get_form(self, transaction, request):
        form = None
        if self.form_class:
            form = self.form_class(payment_method=transaction.payment_method,
                                   transaction=transaction, request=request)

        return form

    def get_template(self, transaction):
        template = select_template([
            'forms/{}/{}/transaction_form.html'.format(
                transaction.document.provider,
                transaction.payment_method.processor.reference
            ),
            'forms/{}/transaction_form.html'.format(
                transaction.payment_method.processor.reference
            ),
            'forms/transaction_form.html'
        ])

        return template

    def __repr__(self):
        return self.reference

    def __unicode__(self):
        return unicode(self.display_name)

    def __str__(self):
        return str(self.display_name)

    def __eq__(self, other):
        return self.__class__ is other.__class__

    def __ne__(self, other):
        return not self.__eq__(other)
