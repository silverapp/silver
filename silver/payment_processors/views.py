# -*- coding: utf-8 -*-
# vim: ft=python:sw=4:ts=4:sts=4:et:

from django.views.generic import View
from django.http import HttpResponse
from rest_framework.exceptions import MethodNotAllowed
from silver.utils.payments import get_payment_complete_url


class GenericTransactionView(View):
    form = None
    template = None
    transaction = None
    request = None

    def get_context_data(self):
        return {
            'payment_method': self.transaction.payment_method,
            'transaction': self.transaction,
            'document': self.transaction.document,
            'customer': self.transaction.customer,
            'provider': self.transaction.provider,
            'entries': list(self.transaction.document._entries),
            'form': self.form,
            'payment_complete_url': get_payment_complete_url(self.transaction,
                                                             self.request)
        }

    def render_template(self):
        return self.template.render(context=self.get_context_data())

    def get(self, request):
        return HttpResponse(self.render_template())

    def post(self, request):
        raise MethodNotAllowed
