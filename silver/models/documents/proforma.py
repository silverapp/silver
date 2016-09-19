# Copyright (c) 2016 Presslabs SRL
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


from decimal import Decimal

from django_fsm import TransitionNotAllowed, transition

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from .base import BillingDocument
from .entries import DocumentEntry
from .invoice import Invoice
from silver.models.billing_entities import Provider
from silver.models.payments import Payment


class Proforma(BillingDocument):
    invoice = models.ForeignKey('Invoice', blank=True, null=True,
                                related_name='related_proforma')

    kind = 'Proforma'

    def __init__(self, *args, **kwargs):
        super(Proforma, self).__init__(*args, **kwargs)

        provider_field = self._meta.get_field("provider")
        provider_field.related_name = "proformas"

        customer_field = self._meta.get_field("customer")
        customer_field.related_name = "proformas"

    @property
    def payment(self):
        try:
            return self.proforma_payment
        except Payment.DoesNotExist:
            return None

    def clean(self):
        super(Proforma, self).clean()
        if not self.series:
            if not hasattr(self, 'provider'):
                # the clean method is called even if the clean_fields method
                # raises exceptions, to we check if the provider was specified
                pass
            elif not self.provider.proforma_series:
                err_msg = {'series': 'You must either specify the series or '
                                     'set a default proforma_series for the '
                                     'provider.'}
                raise ValidationError(err_msg)

    @transition(field='state', source=BillingDocument.STATES.DRAFT,
                target=BillingDocument.STATES.ISSUED)
    def issue(self, issue_date=None, due_date=None):
        self.archived_provider = self.provider.get_proforma_archivable_field_values()

        super(Proforma, self)._issue(issue_date, due_date)

    @transition(field='state', source=BillingDocument.STATES.ISSUED,
                target=BillingDocument.STATES.PAID)
    def pay(self, paid_date=None, affect_related_document=True):
        super(Proforma, self)._pay(paid_date)

        if not self.invoice:
            self.invoice = self._new_invoice()
            self.invoice.issue()
            self.invoice.pay(paid_date=paid_date,
                             affect_related_document=False)

            # if the proforma is paid, the invoice due_date should be issue_date
            self.invoice.due_date = self.invoice.issue_date

            self.invoice.save()
            self.save()

        elif affect_related_document:
            try:
                self.invoice.pay(paid_date=paid_date,
                                 affect_related_document=False)
                self.invoice.save()
            except TransitionNotAllowed:
                # the related invoice is already paid
                # other inconsistencies should've been fixed before
                pass

    @transition(field='state', source=BillingDocument.STATES.ISSUED,
                target=BillingDocument.STATES.CANCELED)
    def cancel(self, cancel_date=None, affect_related_document=True):
        super(Proforma, self)._cancel(cancel_date)

        if self.invoice and affect_related_document:
            self.invoice.cancel(cancel_date=cancel_date,
                                affect_related_document=False)
            self.invoice.save()

    def create_invoice(self):
        if self.state != BillingDocument.STATES.ISSUED:
            raise ValueError("You can't create an invoice from a %s proforma, "
                             "only from an issued one" % self.state)

        if self.invoice:
            raise ValueError("This proforma already has an invoice { %s }"
                             % self.invoice)

        self.invoice = self._new_invoice()
        self.invoice.issue()
        self.invoice.save()

        self.save()

    def _new_invoice(self):
        # Generate the new invoice based this proforma
        invoice_fields = self.fields_for_automatic_invoice_generation
        invoice_fields.update({'proforma': self})
        invoice = Invoice.objects.create(**invoice_fields)

        # For all the entries in the proforma => add the link to the new
        # invoice
        DocumentEntry.objects.filter(proforma=self).update(invoice=invoice)
        return invoice

    @property
    def _starting_number(self):
        return self.provider.proforma_starting_number

    @property
    def default_series(self):
        try:
            return self.provider.proforma_series
        except Provider.DoesNotExist:
            return ''

    @property
    def fields_for_automatic_invoice_generation(self):
        fields = ['customer', 'provider', 'archived_customer',
                  'archived_provider', 'paid_date', 'cancel_date',
                  'sales_tax_percent', 'sales_tax_name', 'currency']
        return {field: getattr(self, field, None) for field in fields}

    @property
    def total(self):
        entries_total = [Decimal(item.total)
                         for item in self.proforma_entries.all()]
        res = sum(entries_total)
        return res

    @property
    def total_before_tax(self):
        entries_total = [Decimal(item.total_before_tax)
                         for item in self.proforma_entries.all()]
        res = sum(entries_total)
        return res

    @property
    def tax_value(self):
        entries_total = [Decimal(item.tax_value)
                         for item in self.proforma_entries.all()]
        res = sum(entries_total)
        return res

    @property
    def related_document(self):
        return self.invoice

    @property
    def fields_for_payment_creation(self):
        fields = super(Proforma, self).fields_for_payment_creation

        proforma_fields = {
            'proforma': self,
            'invoice': self.related_document
        }

        fields.update(proforma_fields)

        return fields


@receiver(pre_delete, sender=Proforma)
def delete_proforma_pdf_from_storage(sender, instance, **kwargs):
    if instance.pdf:
        # Delete the proforma's PDF
        instance.pdf.delete(False)

    # If exists, delete the PDF of the related invoice
    if instance.invoice:
        if instance.invoice.pdf:
            instance.invoice.pdf.delete(False)
