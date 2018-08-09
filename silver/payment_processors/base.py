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

from django.conf import settings
from django.utils.deconstruct import deconstructible
from django.utils.module_loading import import_string
from django.utils.text import slugify
from django.template.loader import select_template


def get_instance(name):
    data = settings.PAYMENT_PROCESSORS[name]
    klass = import_string(data['class'])
    kwargs = data.get('setup_data', {})
    return klass(name, **kwargs)


def get_all_instances():
    choices = []
    for processor_import_path in settings.PAYMENT_PROCESSORS.keys():
        choices.append(get_instance(processor_import_path))
    return choices


@deconstructible
class PaymentProcessorBase(object):
    form_class = None
    template_slug = None
    payment_method_class = None
    transaction_view_class = None
    allowed_currencies = ()

    def __init__(self, name):
        self.name = name

    def get_view(self, transaction, request, **kwargs):
        kwargs.update({
            'form': self.get_form(transaction, request),
            'template': self.get_template(transaction),
            'transaction': transaction,
            'request': request
        })
        return self.transaction_view_class.as_view(**kwargs)

    def get_form(self, transaction, request):
        form = None
        if self.form_class:
            form = self.form_class(payment_method=transaction.payment_method,
                                   transaction=transaction, request=request)

        return form

    def get_template(self, transaction):
        provider = transaction.document.provider
        provider_slug = slugify(provider.company or provider.name)

        template = select_template([
            'forms/{}/{}_transaction_form.html'.format(
                self.template_slug,
                provider_slug
            ),
            'forms/{}/transaction_form.html'.format(
                self.template_slug
            ),
            'forms/transaction_form.html'
        ])

        return template

    def handle_transaction_response(self, transaction, request):
        """
            This method should update the transaction status after the first
            HTTP response from the payment gateway.

            Update transaction's state to Pending or Failed.

            It's called by complete_payment_view.

            If not needed, one can pass it.
        """

        raise NotImplementedError

    def __repr__(self):
        return self.name

    def __str__(self):
        return str(self.name)

    def __eq__(self, other):
        return self.__class__ is other.__class__

    def __ne__(self, other):
        return not self.__eq__(other)
