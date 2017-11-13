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


from django_fsm import TransitionNotAllowed, transition

from django.db import models
from django.apps import apps
from django.db.models.signals import pre_delete, post_save
from django.dispatch import receiver

from .base import BillingDocumentBase, BillingDocumentManager, BillingDocumentQuerySet
from silver.models.billing_entities import Provider


class InvoiceManager(BillingDocumentManager):
    def get_queryset(self):
        queryset = super(BillingDocumentManager, self).get_queryset()
        return queryset.filter(kind='invoice').prefetch_related('invoice_entries__product_code')


class Invoice(BillingDocumentBase):
    objects = InvoiceManager.from_queryset(BillingDocumentQuerySet)()

    class Meta:
        proxy = True

    def __init__(self, *args, **kwargs):
        super(Invoice, self).__init__(*args, **kwargs)

        provider_field = self._meta.get_field("provider")
        provider_field.related_name = "invoices"

        customer_field = self._meta.get_field("customer")
        customer_field.related_name = "invoices"

    @property
    def transactions(self):
        return self.invoice_transactions.all()

    @transition(field='state', source=BillingDocumentBase.STATES.DRAFT,
                target=BillingDocumentBase.STATES.ISSUED)
    def issue(self, issue_date=None, due_date=None):
        self.archived_provider = self.provider.get_invoice_archivable_field_values()

        super(Invoice, self)._issue(issue_date, due_date)

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
    def entries(self):
        return self.invoice_entries.all()


@receiver(pre_delete, sender=Invoice)
def delete_invoice_pdf_from_storage(sender, instance, **kwargs):
    if instance.pdf:
        # Delete the invoice's PDF file
        instance.pdf.pdf_file.delete(False)


@receiver(post_save, sender=Invoice)
def post_invoice_save(sender, instance, created=False, **kwargs):
    if not created:
        return

    Transaction = apps.get_model('silver.Transaction')
    invoice = instance
    proforma = invoice.related_document

    if proforma:
        Transaction.objects.filter(proforma=proforma).update(invoice=invoice)
