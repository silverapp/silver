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

from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from .base import BillingDocument
from silver.models.billing_entities import Provider
from silver.models.payments import Payment


class Invoice(BillingDocument):
    proforma = models.ForeignKey('Proforma', blank=True, null=True,
                                 related_name='related_invoice')

    kind = 'Invoice'

    def __init__(self, *args, **kwargs):
        super(Invoice, self).__init__(*args, **kwargs)

        provider_field = self._meta.get_field("provider")
        provider_field.related_name = "invoices"

        customer_field = self._meta.get_field("customer")
        customer_field.related_name = "invoices"

    @property
    def payment(self):
        try:
            return self.invoice_payment
        except Payment.DoesNotExist:
            return None

    @transition(field='state', source=BillingDocument.STATES.DRAFT,
                target=BillingDocument.STATES.ISSUED)
    def issue(self, issue_date=None, due_date=None):
        self.archived_provider = self.provider.get_invoice_archivable_field_values()

        super(Invoice, self)._issue(issue_date, due_date)

    @transition(field='state', source=BillingDocument.STATES.ISSUED,
                target=BillingDocument.STATES.PAID)
    def pay(self, paid_date=None, affect_related_document=True):
        super(Invoice, self)._pay(paid_date)

        if self.proforma and affect_related_document:
            try:
                self.proforma.pay(paid_date=paid_date,
                                  affect_related_document=False)
                self.proforma.save()
            except TransitionNotAllowed:
                # the related proforma is already paid
                # other inconsistencies should've been fixed before
                pass

    @transition(field='state', source=BillingDocument.STATES.ISSUED,
                target=BillingDocument.STATES.CANCELED)
    def cancel(self, cancel_date=None, affect_related_document=True):
        super(Invoice, self)._cancel(cancel_date)

        if self.proforma and affect_related_document:
            self.proforma.cancel(cancel_date=cancel_date,
                                 affect_related_document=False)
            self.proforma.save()

    @property
    def _starting_number(self):
        return self.provider.invoice_starting_number

    @property
    def default_series(self):
        try:
            return self.provider.invoice_series
        except Provider.DoesNotExist:
            return ''

    @property
    def total(self):
        entries_total = [Decimal(item.total)
                         for item in self.invoice_entries.all()]
        res = sum(entries_total)
        return res

    @property
    def total_before_tax(self):
        entries_total = [Decimal(item.total_before_tax)
                         for item in self.invoice_entries.all()]
        res = sum(entries_total)
        return res

    @property
    def tax_value(self):
        entries_total = [Decimal(item.tax_value)
                         for item in self.invoice_entries.all()]
        res = sum(entries_total)
        return res

    @property
    def related_document(self):
        return self.proforma

    @property
    def fields_for_payment_creation(self):
        fields = super(Invoice, self).fields_for_payment_creation

        invoice_fields = {
            'invoice': self,
            'proforma': self.related_document
        }

        fields.update(invoice_fields)

        return fields


@receiver(pre_delete, sender=Invoice)
def delete_invoice_pdf_from_storage(sender, instance, **kwargs):
    if instance.pdf:
        # Delete the invoice's PDF
        instance.pdf.delete(False)

    # If exists, delete the PDF of the related proforma
    if instance.proforma:
        if instance.proforma.pdf:
            instance.proforma.pdf.delete(False)
