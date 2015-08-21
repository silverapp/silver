from decimal import Decimal

from django.db import models
from django_fsm import transition
from django.db.models.signals import pre_delete
from django.dispatch.dispatcher import receiver

from silver.models.billing_document import BillingDocument
from silver.models.provider import Provider


class Invoice(BillingDocument):
    proforma = models.ForeignKey('Proforma', blank=True, null=True,
                                 related_name='related_proforma')

    kind = 'Invoice'

    def __init__(self, *args, **kwargs):
        super(Invoice, self).__init__(*args, **kwargs)

        provider_field = self._meta.get_field_by_name("provider")[0]
        provider_field.related_name = "invoices"

        customer_field = self._meta.get_field_by_name("customer")[0]
        customer_field.related_name = "invoices"

    @transition(field='state', source=BillingDocument.STATES.DRAFT,
                target=BillingDocument.STATES.ISSUED)
    def issue(self, issue_date=None, due_date=None):
        self.archived_provider = self.provider.get_invoice_archivable_field_values()

        super(Invoice, self).issue(issue_date, due_date)

    @transition(field='state', source=BillingDocument.STATES.ISSUED,
                target=BillingDocument.STATES.PAID)
    def pay(self, paid_date=None, affect_related_document=True):
        super(Invoice, self).pay(paid_date)

        if self.proforma and affect_related_document:
            self.proforma.pay(paid_date=paid_date,
                              affect_related_document=False)
            self.proforma.save()

    @transition(field='state', source=BillingDocument.STATES.ISSUED,
                target=BillingDocument.STATES.CANCELED)
    def cancel(self, cancel_date=None, affect_related_document=True):
        super(Invoice, self).cancel(cancel_date)

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
        res = reduce(lambda x, y: x + y, entries_total, Decimal('0.00'))
        return res

    @property
    def total_before_tax(self):
        entries_total = [Decimal(item.total_before_tax)
                         for item in self.invoice_entries.all()]
        res = reduce(lambda x, y: x + y, entries_total, Decimal('0.0000'))
        return res

    @property
    def tax_value(self):
        entries_total = [Decimal(item.tax_value)
                         for item in self.invoice_entries.all()]
        res = reduce(lambda x, y: x + y, entries_total, Decimal('0.0000'))
        return res

    @property
    def related_document(self):
        return self.proforma


@receiver(pre_delete, sender=Invoice)
def delete_invoice_pdf_from_storage(sender, instance, **kwargs):
    if instance.pdf:
        # Delete the invoice's PDF
        instance.pdf.delete(False)

    # If exists, delete the PDF of the related proforma
    if instance.proforma:
        if instance.proforma.pdf:
            instance.proforma.pdf.delete(False)
