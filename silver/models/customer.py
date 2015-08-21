from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from pyvat import is_vat_number_format_valid
from django_fsm import TransitionNotAllowed

from silver.models.subscription import Subscription
from silver.models.abstract_billing_entity import AbstractBillingEntity


PAYMENT_DUE_DAYS = getattr(settings, 'SILVER_DEFAULT_DUE_DAYS', 5)


class Customer(AbstractBillingEntity):
    payment_due_days = models.PositiveIntegerField(
        default=PAYMENT_DUE_DAYS,
        help_text='Due days for generated proforma/invoice.'
    )
    consolidated_billing = models.BooleanField(
        default=False, help_text='A flag indicating consolidated billing.'
    )
    customer_reference = models.CharField(
        max_length=256, blank=True, null=True,
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

    def __init__(self, *args, **kwargs):
        super(Customer, self).__init__(*args, **kwargs)
        company_field = self._meta.get_field_by_name("company")[0]
        company_field.help_text = "The company to which the bill is issued."

    def clean(self):
        if (self.sales_tax_number and
            is_vat_number_format_valid(self.sales_tax_number,
                                       self.country) is False):
            raise ValidationError(
                {'sales_tax_number': 'The sales tax number is not valid.'}
            )

    def delete(self):
        subscriptions = Subscription.objects.filter(customer=self)
        for sub in subscriptions:
            try:
                sub.cancel()
                sub.save()
            except TransitionNotAllowed:
                pass
        super(Customer, self).delete()

    def get_archivable_field_values(self):
        base_fields = super(Customer, self).get_archivable_field_values()
        customer_fields = ['customer_reference', 'consolidated_billing',
                           'payment_due_days', 'sales_tax_number',
                           'sales_tax_percent']
        fields_dict = {field: getattr(self, field, '') for field in
                       customer_fields}
        base_fields.update(fields_dict)
        return base_fields
