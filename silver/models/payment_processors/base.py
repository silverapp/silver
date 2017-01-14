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

from django.template.loader import select_template
from django.utils.deconstruct import deconstructible


@deconstructible
class PaymentProcessorBase(object):
    reference = None
    form_class = None
    payment_method_class = None
    transaction_view_class = None

    def get_view(self, transaction, request, **kwargs):
        kwargs.update({
            'form': self.get_form(transaction, request),
            'template': self.get_template(transaction),
            'transaction': transaction
        })
        return self.transaction_view_class.as_view(**kwargs)

    def get_form(self, transaction, request):
        if self.form_class:
            return self.form_class(payment_method=transaction.payment_method,
                                   transaction=transaction, request=request)

    def get_template(self, transaction):
        return select_template([
            'forms/{}/{}/transaction_form.html'.format(
                transaction.document.provider,
                transaction.payment_method.payment_processor.reference
            ),
            'forms/{}/transaction_form.html'.format(
                transaction.payment_method.payment_processor.reference
            ),
            'forms/transaction_form.html'
        ])

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
