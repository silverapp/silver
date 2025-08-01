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

from __future__ import absolute_import

from django_fsm import TransitionNotAllowed

from django.core.exceptions import ValidationError
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from silver.models.billing_entities import Provider
from silver.models.documents.base import (
    BillingDocumentBase, BillingDocumentManager, BillingDocumentQuerySet)
from silver.models.documents.entries import DocumentEntry
from silver.models.documents.invoice import Invoice
from silver.utils.transition import locking_atomic_transition


class ProformaManager(BillingDocumentManager):
    def get_queryset(self):
        queryset = super(BillingDocumentManager, self).get_queryset()
        return queryset.filter(kind='proforma').prefetch_related('proforma_entries__product_code',
                                                                 'proforma_entries__invoice')


class Proforma(BillingDocumentBase):
    objects = ProformaManager.from_queryset(BillingDocumentQuerySet)()

    class Meta:
        proxy = True

    def __init__(self, *args, **kwargs):
        super(Proforma, self).__init__(*args, **kwargs)

        provider_field = self._meta.get_field("provider")
        provider_field.related_name = "proformas"

        customer_field = self._meta.get_field("customer")
        customer_field.related_name = "proformas"

    @property
    def transactions(self):
        return self.proforma_transactions.all()

    def clean(self):
        super(Proforma, self).clean()
        if self.is_storno:
            raise ValidationError({"is_storno": "A proforma cannot be a storno."})

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

    @locking_atomic_transition(field='state', source=BillingDocumentBase.STATES.DRAFT,
                               target=BillingDocumentBase.STATES.ISSUED)
    def issue(self, issue_date=None, due_date=None):
        self.archived_provider = self.provider.get_archivable_field_values()

        self._issue(issue_date, due_date)

    @locking_atomic_transition(field='state', source=BillingDocumentBase.STATES.ISSUED,
                               target=BillingDocumentBase.STATES.PAID)
    def pay(self, paid_date=None):
        self._pay(paid_date)

        if not self.related_document:
            self.related_document = self._new_invoice()
            self.save()

            self.related_document.issue()
            self.related_document.save()

    def create_invoice(self, use_proforma_issue_date=False):
        if self.state != BillingDocumentBase.STATES.ISSUED:
            raise ValueError("You can't create an invoice from a %s proforma, "
                             "only from an issued one" % self.state)

        if self.related_document:
            raise ValueError("This proforma already has an invoice { %s }"
                             % self.related_document)

        self.related_document = self._new_invoice()
        self.related_document.issue(issue_date=self.issue_date if use_proforma_issue_date else None)

        self.save()

        return self.related_document

    def _new_invoice(self):
        # Generate the new invoice based this proforma
        invoice_fields = self.fields_for_automatic_invoice_generation
        invoice_fields.update({'related_document': self})
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
                  'sales_tax_percent', 'sales_tax_name', 'currency',
                  'transaction_currency', 'transaction_xe_rate',
                  'transaction_xe_date']
        return {field: getattr(self, field, None) for field in fields}

    @property
    def entries(self):
        return self.proforma_entries.all()

    @property
    def invoice(self):
        return self.related_document


@receiver(pre_delete, sender=Proforma)
def delete_proforma_pdf_from_storage(sender, instance, **kwargs):
    if instance.pdf:
        # Delete the proforma's PDF
        instance.pdf.pdf_file.delete(False)
