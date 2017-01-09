from decimal import Decimal

from django.db import models

from silver.models import DocumentEntry


class Document(models.Model):
    kind = models.CharField(max_length=40)

    @property
    def total(self):
        data = {
            'invoice_id': self.id
        } if self.kind == 'invoice' else {
            'proforma_id': self.id
        }

        entries = DocumentEntry.objects.filter(**data)
        entries_total = [Decimal(entry.total) for entry in entries.all()]

        return sum(entries_total)

    series = models.CharField(max_length=20, blank=True, null=True)
    number = models.IntegerField(blank=True, null=True)
    customer = models.ForeignKey('Customer')
    provider = models.ForeignKey('Provider')
    due_date = models.DateField(null=True, blank=True)
    issue_date = models.DateField(null=True, blank=True)
    paid_date = models.DateField(null=True, blank=True)
    cancel_date = models.DateField(null=True, blank=True)
    sales_tax_percent = models.DecimalField(max_digits=4, decimal_places=2,
                                            null=True, blank=True)
    sales_tax_name = models.CharField(max_length=64, blank=True, null=True)
    currency = models.CharField(max_length=4)
    state = models.CharField(max_length=10)
    pdf = models.FileField(null=True, blank=True, editable=False)

    class Meta:
        managed = False
