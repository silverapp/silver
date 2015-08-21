from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.dispatch.dispatcher import receiver
from django.db.models.signals import pre_save
from model_utils import Choices

from silver.models import *


class Provider(AbstractBillingEntity):
    class FLOWS(object):
        PROFORMA = 'proforma'
        INVOICE = 'invoice'

    FLOW_CHOICES = Choices(
        (FLOWS.PROFORMA, _('Proforma')),
        (FLOWS.INVOICE, _('Invoice')),
    )

    class DEFAULT_DOC_STATE(object):
        DRAFT = 'draft'
        ISSUED = 'issued'

    DOCUMENT_DEFAULT_STATE = Choices(
        (DEFAULT_DOC_STATE.DRAFT, _('Draft')),
        (DEFAULT_DOC_STATE.ISSUED, _('Issued')))

    flow = models.CharField(
        max_length=10, choices=FLOW_CHOICES,
        default=FLOWS.PROFORMA,
        help_text="One of the available workflows for generating proformas and\
                   invoices (see the documentation for more details)."
    )
    invoice_series = models.CharField(
        max_length=20,
        help_text="The series that will be used on every invoice generated by\
                   this provider."
    )
    invoice_starting_number = models.PositiveIntegerField()
    proforma_series = models.CharField(
        max_length=20, blank=True, null=True,
        help_text="The series that will be used on every proforma generated by\
                   this provider."
    )
    proforma_starting_number = models.PositiveIntegerField(
        blank=True, null=True
    )
    default_document_state = models.CharField(
        max_length=10, choices=DOCUMENT_DEFAULT_STATE,
        default=DOCUMENT_DEFAULT_STATE.draft,
        help_text="The default state of the auto-generated documents."
    )

    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        company_field = self._meta.get_field_by_name("company")[0]
        company_field.help_text = "The provider issuing the invoice."

    def clean(self):
        if self.flow == self.FLOWS.PROFORMA:
            if not self.proforma_starting_number and\
               not self.proforma_series:
                errors = {'proforma_series': "This field is required as the "
                                             "chosen flow is proforma.",
                          'proforma_starting_number': "This field is required "
                                                      "as the chosen flow is "
                                                      "proforma."}
                raise ValidationError(errors)
            elif not self.proforma_series:
                errors = {'proforma_series': "This field is required as the "
                                             "chosen flow is proforma."}
                raise ValidationError(errors)
            elif not self.proforma_starting_number:
                errors = {'proforma_starting_number': "This field is required "
                                                      "as the chosen flow is "
                                                      "proforma."}
                raise ValidationError(errors)

    def get_invoice_archivable_field_values(self):
        base_fields = super(Provider, self).get_archivable_field_values()
        base_fields.update({'invoice_series': getattr(self, 'invoice_series', '')})
        return base_fields

    def get_proforma_archivable_field_values(self):
        base_fields = super(Provider, self).get_archivable_field_values()
        base_fields.update({'proforma_series': getattr(self, 'proforma_series', '')})
        return base_fields

    @property
    def model_corresponding_to_default_flow(self):
        return Proforma if self.flow == self.FLOWS.PROFORMA else Invoice


@receiver(pre_save, sender=Provider)
def update_draft_billing_documents(sender, instance, **kwargs):
    if instance.pk:
        provider = Provider.objects.get(pk=instance.pk)
        old_invoice_series = provider.invoice_series
        old_proforma_series = provider.proforma_series

        if instance.invoice_series != old_invoice_series:
            for invoice in Invoice.objects.filter(state='draft',
                                                  provider=provider):
                # update the series for draft invoices
                invoice.series = instance.invoice_series
                invoice.number = invoice._generate_number(
                    instance.invoice_starting_number
                )
                invoice.save()

        if instance.proforma_series != old_proforma_series:
            for proforma in Proforma.objects.filter(state='draft',
                                                    provider=provider):
                # update the series for draft invoices
                proforma.series = instance.proforma_series
                proforma.number = proforma._generate_number(
                    instance.proforma_starting_number
                )
                proforma.save()
