from decimal import Decimal

from django.db import models
from django.core.validators import MinValueValidator


class DocumentEntry(models.Model):
    description = models.CharField(max_length=1024)
    unit = models.CharField(max_length=1024, blank=True, null=True)
    quantity = models.DecimalField(max_digits=19, decimal_places=4,
                                   validators=[MinValueValidator(0.0)])
    unit_price = models.DecimalField(max_digits=19, decimal_places=4)
    product_code = models.ForeignKey('ProductCode', null=True, blank=True,
                                     related_name='invoices')
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    prorated = models.BooleanField(default=False)
    invoice = models.ForeignKey('Invoice', related_name='invoice_entries',
                                blank=True, null=True)
    proforma = models.ForeignKey('Proforma', related_name='proforma_entries',
                                 blank=True, null=True)

    class Meta:
        verbose_name = 'Entry'
        verbose_name_plural = 'Entries'

    @property
    def total(self):
        res = self.total_before_tax + self.tax_value
        return res.quantize(Decimal('0.0000'))

    @property
    def total_before_tax(self):
        res = Decimal(self.quantity * self.unit_price)
        return res.quantize(Decimal('0.0000'))

    @property
    def tax_value(self):
        if self.invoice:
            sales_tax_percent = self.invoice.sales_tax_percent
        elif self.proforma:
            sales_tax_percent = self.proforma.sales_tax_percent
        else:
            sales_tax_percent = None

        if not sales_tax_percent:
            return Decimal(0)

        res = Decimal(self.total_before_tax * sales_tax_percent / 100)
        return res.quantize(Decimal('0.0000'))

    def __unicode__(self):
        s = u'{descr} - {unit} - {unit_price} - {quantity} - {product_code}'
        return s.format(
            descr=self.description,
            unit=self.unit,
            unit_price=self.unit_price,
            quantity=self.quantity,
            product_code=self.product_code
        )
