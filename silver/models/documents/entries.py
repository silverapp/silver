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


from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


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
        return res.quantize(Decimal('0.00'))

    @property
    def total_before_tax(self):
        res = Decimal(self.quantity * self.unit_price)
        return res.quantize(Decimal('0.00'))

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
        return res.quantize(Decimal('0.00'))

    def clone(self):
        return DocumentEntry(
            description=self.description,
            unit=self.unit,
            quantity=self.quantity,
            unit_price=self.unit_price,
            product_code=self.product_code,
            start_date=self.start_date,
            end_date=self.end_date,
            prorated=self.prorated
        )

    def __unicode__(self):
        s = u'{descr} - {unit} - {unit_price} - {quantity} - {product_code}'
        return s.format(
            descr=self.description,
            unit=self.unit,
            unit_price=self.unit_price,
            quantity=self.quantity,
            product_code=self.product_code
        )
