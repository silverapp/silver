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

from datetime import datetime, timedelta
from decimal import Decimal

from django_fsm import TransitionNotAllowed, FSMField, transition
from django_xhtml2pdf.utils import generate_pdf_template_object
from jsonfield import JSONField
from model_utils import Choices

from django.conf import settings
from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
from django.core.files.base import ContentFile
from django.core.urlresolvers import reverse
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Max
from django.db.models.signals import pre_delete, pre_save
from django.dispatch import receiver
from django.http import HttpResponse
from django.template.loader import select_template
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _
from django.utils.module_loading import import_string

from .billing_entities import Customer, Provider
from silver.utils.international import currencies


_storage = getattr(settings, 'SILVER_DOCUMENT_STORAGE', None)
if _storage:
    _storage_klass = import_string(_storage[0])
    _storage = _storage_klass(*_storage[1], **_storage[2])


PAYMENT_DUE_DAYS = getattr(settings, 'SILVER_DEFAULT_DUE_DAYS', 5)


def documents_pdf_path(document, filename):
    path = '{prefix}{company}/{doc_name}/{date}/{filename}'.format(
        company=slugify(unicode(
            document.provider.company or document.provider.name)),
        date=document.issue_date.strftime('%Y/%m'),
        doc_name=('%ss' % document.__class__.__name__).lower(),
        prefix=getattr(settings, 'SILVER_DOCUMENT_PREFIX', ''),
        filename=filename)
    return path


class BillingDocument(models.Model):
    class STATES(object):
        DRAFT = 'draft'
        ISSUED = 'issued'
        PAID = 'paid'
        CANCELED = 'canceled'

    STATE_CHOICES = Choices(
        (STATES.DRAFT, _('Draft')),
        (STATES.ISSUED, _('Issued')),
        (STATES.PAID, _('Paid')),
        (STATES.CANCELED, _('Canceled'))
    )

    series = models.CharField(max_length=20, blank=True, null=True,
                              db_index=True)
    number = models.IntegerField(blank=True, null=True, db_index=True)
    customer = models.ForeignKey('Customer')
    provider = models.ForeignKey('Provider')
    archived_customer = JSONField()
    archived_provider = JSONField()
    due_date = models.DateField(null=True, blank=True)
    issue_date = models.DateField(null=True, blank=True, db_index=True)
    paid_date = models.DateField(null=True, blank=True)
    cancel_date = models.DateField(null=True, blank=True)
    sales_tax_percent = models.DecimalField(max_digits=4, decimal_places=2,
                                            validators=[MinValueValidator(0.0)],
                                            null=True, blank=True)
    sales_tax_name = models.CharField(max_length=64, blank=True, null=True)
    currency = models.CharField(
        choices=currencies, max_length=4, default='USD',
        help_text='The currency used for billing.')
    pdf = models.FileField(null=True, blank=True, editable=False,
                           storage=_storage, upload_to=documents_pdf_path)
    state = FSMField(choices=STATE_CHOICES, max_length=10, default=STATES.DRAFT,
                     verbose_name="State",
                     help_text='The state the invoice is in.')

    _last_state = None

    class Meta:
        abstract = True
        unique_together = ('provider', 'series', 'number')
        ordering = ('-issue_date', 'series', '-number')

    def __init__(self, *args, **kwargs):
        super(BillingDocument, self).__init__(*args, **kwargs)
        self._last_state = self.state

    def _issue(self, issue_date=None, due_date=None):
        if issue_date:
            self.issue_date = datetime.strptime(issue_date, '%Y-%m-%d').date()
        elif not self.issue_date and not issue_date:
            self.issue_date = timezone.now().date()

        if due_date:
            self.due_date = datetime.strptime(due_date, '%Y-%m-%d').date()
        elif not self.due_date and not due_date:
            delta = timedelta(days=PAYMENT_DUE_DAYS)
            self.due_date = timezone.now().date() + delta

        if not self.sales_tax_name:
            self.sales_tax_name = self.customer.sales_tax_name
        if not self.sales_tax_percent:
            self.sales_tax_percent = self.customer.sales_tax_percent

        if not self.number:
            self.number = self._generate_number()

        self.archived_customer = self.customer.get_archivable_field_values()

        self._save_pdf(state=self.STATES.ISSUED)

    @transition(field=state, source=STATES.DRAFT, target=STATES.ISSUED)
    def issue(self, issue_date=None, due_date=None):
        self._issue(issue_date=issue_date, due_date=due_date)

    def _pay(self, paid_date=None):
        if paid_date:
            self.paid_date = datetime.strptime(paid_date, '%Y-%m-%d').date()
        if not self.paid_date and not paid_date:
            self.paid_date = timezone.now().date()

        self._save_pdf(state=self.STATES.PAID)

    @transition(field=state, source=STATES.ISSUED, target=STATES.PAID)
    def pay(self, paid_date=None):
        self._pay(paid_date=paid_date)

    def _cancel(self, cancel_date=None):
        if cancel_date:
            self.cancel_date = datetime.strptime(cancel_date, '%Y-%m-%d').date()
        if not self.cancel_date and not cancel_date:
            self.cancel_date = timezone.now().date()

        self._save_pdf(state=self.STATES.CANCELED)

    @transition(field=state, source=STATES.ISSUED, target=STATES.CANCELED)
    def cancel(self, cancel_date=None):
        self._cancel(cancel_date=cancel_date)

    def clone_into_draft(self):
        copied_fields = {
            'customer': self.customer,
            'provider': self.provider,
            'currency': self.currency,
            'sales_tax_percent': self.sales_tax_percent,
            'sales_tax_name': self.sales_tax_name
        }

        clone = self.__class__._default_manager.create(**copied_fields)
        clone.state = self.STATES.DRAFT

        # clone entries too
        for entry in self._entries:
            entry.pk = None
            entry.id = None
            if isinstance(self, Proforma):
                entry.proforma = clone
                entry.invoice = None
            elif isinstance(self, Invoice):
                entry.invoice = clone
                entry.proforma = None
            entry.save()

        clone.save()

        return clone

    def clean(self):
        super(BillingDocument, self).clean()

        # The only change that is allowed if the document is in issued state
        # is the state chage from issued to paid
        # !! TODO: If _last_state == 'issued' and self.state == 'paid' || 'canceled'
        # it should also be checked that the other fields are the same bc.
        # right now a document can be in issued state and someone could
        # send a request which contains the state = 'paid' and also send
        # other changed fields and the request would be accepted bc. only
        # the state is verified.
        if self._last_state == self.STATES.ISSUED and\
           self.state not in [self.STATES.PAID, self.STATES.CANCELED]:
            msg = 'You cannot edit the document once it is in issued state.'
            raise ValidationError({NON_FIELD_ERRORS: msg})

        if self._last_state == self.STATES.CANCELED:
            msg = 'You cannot edit the document once it is in canceled state.'
            raise ValidationError({NON_FIELD_ERRORS: msg})

        # If it's in paid state => don't allow any changes
        if self._last_state == self.STATES.PAID:
            msg = 'You cannot edit the document once it is in paid state.'
            raise ValidationError({NON_FIELD_ERRORS: msg})

    def save(self, *args, **kwargs):
        if not self.series:
            self.series = self.default_series

        # Generate the number
        if not self.number and self.state != BillingDocument.STATES.DRAFT:
            self.number = self._generate_number()

        # Add tax info
        if not self.sales_tax_name:
            self.sales_tax_name = self.customer.sales_tax_name
        if not self.sales_tax_percent:
            self.sales_tax_percent = self.customer.sales_tax_percent

        self._last_state = self.state
        super(BillingDocument, self).save(*args, **kwargs)

    def _generate_number(self, default_starting_number=1):
        """Generates the number for a proforma/invoice."""
        default_starting_number = max(default_starting_number, 1)

        documents = self.__class__._default_manager.filter(
            provider=self.provider, series=self.series
        )
        if not documents.exists():
            # An invoice/proforma with this provider and series does not exist
            if self.series == self.default_series:
                return self._starting_number
            else:
                return default_starting_number
        else:
            # An invoice with this provider and series already exists
            max_existing_number = documents.aggregate(
                Max('number')
            )['number__max']
            if max_existing_number:
                if self._starting_number and self.series == self.default_series:
                    return max(max_existing_number + 1, self._starting_number)
                else:
                    return max_existing_number + 1
            else:
                return default_starting_number

    def series_number(self):
        if self.series:
            if self.number:
                return "%s-%d" % (self.series, self.number)
            else:
                return "%s-draft-id:%d" % (self.series, self.pk)

        else:
            return "draft-id:%d" % self.pk

    series_number.short_description = 'Number'
    series_number = property(series_number)

    def __unicode__(self):
        return u'%s %s => %s [%.2f %s]' % (self.series_number,
                                           self.provider.billing_name,
                                           self.customer.billing_name,
                                           self.total, self.currency)

    @property
    def updateable_fields(self):
        return ['customer', 'provider', 'due_date', 'issue_date', 'paid_date',
                'cancel_date', 'sales_tax_percent', 'sales_tax_name',
                'currency']

    @property
    def admin_change_url(self):
        url_base = 'admin:{app_label}_{klass}_change'.format(
            app_label=self._meta.app_label,
            klass=self.__class__.__name__.lower())
        url = reverse(url_base, args=(self.pk,))
        return '<a href="{url}">{display_series}</a>'.format(
            url=url, display_series=self.series_number)

    @property
    def _entries(self):
        # entries iterator which replaces the invoice/proforma from the DB with
        # self. We need this in _generate_pdf so that the data in PDF has the
        # lastest state for the document. Without this we get in template:
        #
        # invoice.issue_date != entry.invoice.issue_date
        #
        # which is obviously false.
        document_type_name = self.__class__.__name__  # Invoice or Proforma
        kwargs = {document_type_name.lower(): self}
        entries = DocumentEntry.objects.filter(**kwargs)
        for entry in entries:
            if document_type_name.lower() == 'invoice':
                entry.invoice = self
            if document_type_name.lower() == 'proforma':
                entry.proforma = self
            yield(entry)

    def _generate_pdf(self, state=None):
        customer = Customer(**self.archived_customer)
        provider = Provider(**self.archived_provider)
        if state is None:
            state = self.state

        context = {
            'document': self,
            'provider': provider,
            'customer': customer,
            'entries': self._entries,
            'state': state
        }

        provider_state_template = '{provider}/{kind}_{state}_pdf.html'.format(
            kind=self.kind, provider=self.provider.slug, state=state).lower()
        provider_template = '{provider}/{kind}_pdf.html'.format(
            kind=self.kind, provider=self.provider.slug).lower()
        generic_state_template = '{kind}_{state}_pdf.html'.format(
            kind=self.kind, state=state).lower()
        generic_template = '{kind}_pdf.html'.format(
            kind=self.kind).lower()
        _templates = [provider_state_template, provider_template,
                      generic_state_template, generic_template]

        templates = []
        for t in _templates:
            templates.append('billing_documents/' + t)

        template = select_template(templates)

        file_object = HttpResponse(content_type='application/pdf')
        generate_pdf_template_object(template, file_object, context)

        return file_object

    def _save_pdf(self, state=None):
        file_object = self._generate_pdf(state)

        if file_object:
            pdf_content = ContentFile(file_object)
            filename = '{doc_type}_{series}-{number}.pdf'.format(
                doc_type=self.__class__.__name__,
                series=self.series,
                number=self.number
            )

            if self.pdf:
                self.pdf.delete()
            self.pdf.save(filename, pdf_content, True)
        else:
            raise RuntimeError(_('Could not generate invoice pdf.'))

    def serialize_hook(self, hook):
        """
        Used to generate a skinny payload.
        """

        return {
            'hook': hook.dict(),
            'data': {
                'id': self.id
            }
        }


class Invoice(BillingDocument):
    proforma = models.ForeignKey('Proforma', blank=True, null=True,
                                 related_name='related_proforma')

    kind = 'Invoice'

    def __init__(self, *args, **kwargs):
        super(Invoice, self).__init__(*args, **kwargs)

        provider_field = self._meta.get_field("provider")
        provider_field.related_name = "invoices"

        customer_field = self._meta.get_field("customer")
        customer_field.related_name = "invoices"

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


@receiver(pre_delete, sender=Invoice)
def delete_invoice_pdf_from_storage(sender, instance, **kwargs):
    if instance.pdf:
        # Delete the invoice's PDF
        instance.pdf.delete(False)

    # If exists, delete the PDF of the related proforma
    if instance.proforma:
        if instance.proforma.pdf:
            instance.proforma.pdf.delete(False)


class Proforma(BillingDocument):
    invoice = models.ForeignKey('Invoice', blank=True, null=True,
                                related_name='related_invoice')

    kind = 'Proforma'

    def __init__(self, *args, **kwargs):
        super(Proforma, self).__init__(*args, **kwargs)

        provider_field = self._meta.get_field("provider")
        provider_field.related_name = "proformas"

        customer_field = self._meta.get_field("customer")
        customer_field.related_name = "proformas"

    def clean(self):
        super(Proforma, self).clean()
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

    @transition(field='state', source=BillingDocument.STATES.DRAFT,
                target=BillingDocument.STATES.ISSUED)
    def issue(self, issue_date=None, due_date=None):
        self.archived_provider = self.provider.get_proforma_archivable_field_values()

        super(Proforma, self)._issue(issue_date, due_date)

    @transition(field='state', source=BillingDocument.STATES.ISSUED,
                target=BillingDocument.STATES.PAID)
    def pay(self, paid_date=None, affect_related_document=True):
        super(Proforma, self)._pay(paid_date)

        if not self.invoice:
            self.invoice = self._new_invoice()
            self.invoice.issue()
            self.invoice.pay(paid_date=paid_date,
                             affect_related_document=False)

            # if the proforma is paid, the invoice due_date should be issue_date
            self.invoice.due_date = self.invoice.issue_date

            self.invoice.save()
            self.save()

        elif affect_related_document:
            try:
                self.invoice.pay(paid_date=paid_date,
                                 affect_related_document=False)
                self.invoice.save()
            except TransitionNotAllowed:
                # the related invoice is already paid
                # other inconsistencies should've been fixed before
                pass

    @transition(field='state', source=BillingDocument.STATES.ISSUED,
                target=BillingDocument.STATES.CANCELED)
    def cancel(self, cancel_date=None, affect_related_document=True):
        super(Proforma, self)._cancel(cancel_date)

        if self.invoice and affect_related_document:
            self.invoice.cancel(cancel_date=cancel_date,
                                affect_related_document=False)
            self.invoice.save()

    def create_invoice(self):
        if self.state != BillingDocument.STATES.ISSUED:
            raise ValueError("You can't create an invoice from a %s proforma, "
                             "only from an issued one" % self.state)

        if self.invoice:
            raise ValueError("This proforma already has an invoice { %s }"
                             % self.invoice)

        self.invoice = self._new_invoice()
        self.invoice.issue()
        self.invoice.save()

        self.save()

    def _new_invoice(self):
        # Generate the new invoice based this proforma
        invoice_fields = self.fields_for_automatic_invoice_generation
        invoice_fields.update({'proforma': self})
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
                  'sales_tax_percent', 'sales_tax_name', 'currency']
        return {field: getattr(self, field, None) for field in fields}

    @property
    def total(self):
        entries_total = [Decimal(item.total)
                         for item in self.proforma_entries.all()]
        res = sum(entries_total)
        return res

    @property
    def total_before_tax(self):
        entries_total = [Decimal(item.total_before_tax)
                         for item in self.proforma_entries.all()]
        res = sum(entries_total)
        return res

    @property
    def tax_value(self):
        entries_total = [Decimal(item.tax_value)
                         for item in self.proforma_entries.all()]
        res = sum(entries_total)
        return res

    @property
    def related_document(self):
        return self.invoice


@receiver(pre_delete, sender=Proforma)
def delete_proforma_pdf_from_storage(sender, instance, **kwargs):
    if instance.pdf:
        # Delete the proforma's PDF
        instance.pdf.delete(False)

    # If exists, delete the PDF of the related invoice
    if instance.invoice:
        if instance.invoice.pdf:
            instance.invoice.pdf.delete(False)


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

    def __unicode__(self):
        s = u'{descr} - {unit} - {unit_price} - {quantity} - {product_code}'
        return s.format(
            descr=self.description,
            unit=self.unit,
            unit_price=self.unit_price,
            quantity=self.quantity,
            product_code=self.product_code
        )


@receiver(pre_save, sender=Provider)
def update_draft_billing_documents(sender, instance, **kwargs):
    if instance.pk and not kwargs.get('raw', False):
        provider = Provider.objects.get(pk=instance.pk)
        old_invoice_series = provider.invoice_series
        old_proforma_series = provider.proforma_series

        if instance.invoice_series != old_invoice_series:
            for invoice in Invoice.objects.filter(state='draft',
                                                  provider=provider):
                # update the series for draft invoices
                invoice.series = instance.invoice_series
                invoice.number = None
                invoice.save()

        if instance.proforma_series != old_proforma_series:
            for proforma in Proforma.objects.filter(state='draft',
                                                    provider=provider):
                # update the series for draft invoices
                proforma.series = instance.proforma_series
                proforma.number = None
                proforma.save()