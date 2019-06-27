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

from pyvat import is_vat_number_format_valid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.html import escape
from django.urls import reverse

from silver.utils.international import currencies
from silver.models.billing_entities.base import BaseBillingEntity
from silver.validators import validate_reference


PAYMENT_DUE_DAYS = getattr(settings, 'SILVER_DEFAULT_DUE_DAYS', 5)


class Customer(BaseBillingEntity):
    class Meta:
        index_together = (('first_name', 'last_name', 'company'),)
        ordering = ['first_name', 'last_name', 'company']

    first_name = models.CharField(
        max_length=128,
        help_text='The customer\'s first name.'
    )
    last_name = models.CharField(
        max_length=128,
        help_text='The customer\'s last name.'
    )

    payment_due_days = models.PositiveIntegerField(
        default=PAYMENT_DUE_DAYS,
        help_text='Due days for generated proforma/invoice.'
    )
    consolidated_billing = models.BooleanField(
        default=False, help_text='A flag indicating consolidated billing.'
    )
    customer_reference = models.CharField(
        max_length=256, blank=True, null=True, validators=[validate_reference],
        help_text="It's a reference to be passed between silver and clients. "
                  "It usually points to an account ID."
    )
    sales_tax_number = models.CharField(max_length=64, blank=True, null=True)
    sales_tax_percent = models.DecimalField(
        max_digits=4, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0.0)],
        help_text="Whenever to add sales tax. "
                  "If null, it won't show up on the invoice."
    )
    sales_tax_name = models.CharField(
        max_length=64, null=True, blank=True,
        help_text="Sales tax name (eg. 'sales tax' or 'VAT')."
    )

    currency = models.CharField(
        choices=currencies, max_length=4, null=True, blank=True,
        help_text="Used to enforce a certain currency when making transactions"
                  "for the customer."
    )

    def __init__(self, *args, **kwargs):
        archived_name = None
        if 'name' in kwargs:
            archived_name = kwargs.pop('name')

        super(Customer, self).__init__(*args, **kwargs)

        if archived_name:
            self.first_name, self.last_name = archived_name.split()

        company_field = self._meta.get_field("company")
        company_field.help_text = "The company to which the bill is issued."

    def clean(self):
        if (self.sales_tax_number and
            is_vat_number_format_valid(self.sales_tax_number,
                                       self.country) is False):
            raise ValidationError(
                {'sales_tax_number': 'The sales tax number is not valid.'}
            )

    def get_archivable_field_values(self):
        base_fields = super(Customer, self).get_archivable_field_values()
        customer_fields = ['first_name', 'last_name', 'customer_reference', 'consolidated_billing',
                           'payment_due_days', 'sales_tax_number', 'sales_tax_percent']
        fields_dict = {field: getattr(self, field, '') for field in
                       customer_fields}
        base_fields.update(fields_dict)
        return base_fields

    @property
    def name(self):
        return u"%s %s" % (self.first_name, self.last_name)

    @property
    def admin_change_url(self):
        display = escape(self.name)
        if self.company:
            display += "<hr> " + escape(self.company)

        link = reverse("admin:silver_customer_change", args=[self.pk])
        return u'<a href="%s">%s</a>' % (link, display)

    def __str__(self):
        return self.name
