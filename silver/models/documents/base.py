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


import logging
from datetime import datetime, timedelta
from decimal import Decimal

import pytz
from django_fsm import FSMField, transition, TransitionNotAllowed
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
from django.http import HttpResponse
from django.template.loader import select_template
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _
from django.utils.module_loading import import_string

from silver.models.billing_entities import Customer, Provider
from silver.currencies import CurrencyConverter, RateNotFound
from silver.utils.international import currencies

from .entries import DocumentEntry


_storage = getattr(settings, 'SILVER_DOCUMENT_STORAGE', None)
if _storage:
    _storage_klass = import_string(_storage[0])
    _storage = _storage_klass(*_storage[1], **_storage[2])


PAYMENT_DUE_DAYS = getattr(settings, 'SILVER_DEFAULT_DUE_DAYS', 5)

logger = logging.getLogger(__name__)


def documents_pdf_path(document, filename):
    path = '{prefix}{company}/{doc_name}/{date}/{filename}'.format(
        company=slugify(unicode(
            document.provider.company or document.provider.name)),
        date=document.issue_date.strftime('%Y/%m'),
        doc_name=('%ss' % document.__class__.__name__).lower(),
        prefix=getattr(settings, 'SILVER_DOCUMENT_PREFIX', ''),
        filename=filename)
    return path


class BillingDocumentQuerySet(models.QuerySet):
    def due_this_month(self):
        return self.filter(
            state=BillingDocumentBase.STATES.ISSUED,
            due_date__gte=datetime.now(pytz.utc).date().replace(day=1)
        )

    def due_today(self):
        return self.filter(
            state=BillingDocumentBase.STATES.ISSUED,
            due_date__exact=datetime.now(pytz.utc).date()
        )

    def overdue(self):
        return self.filter(
            state=BillingDocumentBase.STATES.ISSUED,
            due_date__lt=datetime.now(pytz.utc).date()
        )

    def overdue_since_last_month(self):
        return self.filter(
            state=BillingDocumentBase.STATES.ISSUED,
            due_date__lt=datetime.now(pytz.utc).date().replace(day=1)
        )


class BillingDocumentManager(models.Manager):
    def get_queryset(self):
        queryset = super(BillingDocumentManager, self).get_queryset()
        queryset = queryset.select_related('customer', 'provider')
        if (self.model.kind == 'Invoice'):
            queryset = queryset.prefetch_related('invoice_entries__product_code')
        if (self.model.kind == 'Proforma'):
            queryset = queryset.prefetch_related('proforma_entries__product_code',
                                                 'proforma_entries__invoice')
        return queryset


class BillingDocumentBase(models.Model):
    objects = BillingDocumentManager.from_queryset(BillingDocumentQuerySet)()

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
        help_text='The currency used for billing.'
    )
    transaction_currency = models.CharField(
        choices=currencies, max_length=4,
        help_text='The currency used when making a transaction.'
    )
    transaction_xe_rate = models.DecimalField(
        max_digits=16, decimal_places=4, null=True, blank=True,
        help_text='Currency exchange rate from document currency to '
                  'transaction_currency.'
    )
    transaction_xe_date = models.DateField(
        null=True, blank=True,
        help_text='Date of the transaction exchange rate.'
    )

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
        super(BillingDocumentBase, self).__init__(*args, **kwargs)
        self._last_state = self.state

    def _issue(self, issue_date=None, due_date=None):
        if issue_date:
            self.issue_date = datetime.strptime(issue_date, '%Y-%m-%d').date()
        elif not self.issue_date and not issue_date:
            self.issue_date = timezone.now().date()

        if not self.transaction_xe_rate:
            if not self.transaction_xe_date:
                self.transaction_xe_date = self.issue_date

            try:
                xe_rate = CurrencyConverter.convert(1, self.currency,
                                                    self.transaction_currency,
                                                    self.transaction_xe_date)
            except RateNotFound:
                raise TransitionNotAllowed('Couldn\'t automatically obtain an '
                                           'exchange rate.')

            self.transaction_xe_rate = xe_rate

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
            entry_clone = entry.clone()
            document_type_name = self.__class__.__name__.lower()
            setattr(entry_clone, document_type_name, clone)
            entry_clone.save()

        clone.save()

        return clone

    def clean(self):
        super(BillingDocumentBase, self).clean()

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
        if not self.transaction_currency:
            self.transaction_currency = self.customer.currency or self.currency

        if not self.series:
            self.series = self.default_series

        # Generate the number
        if not self.number and self.state != BillingDocumentBase.STATES.DRAFT:
            self.number = self._generate_number()

        # Add tax info
        if not self.sales_tax_name:
            self.sales_tax_name = self.customer.sales_tax_name
        if not self.sales_tax_percent:
            self.sales_tax_percent = self.customer.sales_tax_percent

        self._last_state = self.state
        super(BillingDocumentBase, self).save(*args, **kwargs)

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
        # self. We need this in generate_pdf so that the data in PDF has the
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

    @property
    def transactions(self):
        return self.transaction_set.all()

    @property
    def transaction_total(self):
        if self.transaction_xe_rate:
            return Decimal(self.total * self.transaction_xe_rate).quantize(
                Decimal('0.00')
            )

    def get_template_context(self, state=None):
        customer = Customer(**self.archived_customer)
        provider = Provider(**self.archived_provider)
        if state is None:
            state = self.state

        return {
            'document': self,
            'provider': provider,
            'customer': customer,
            'entries': self._entries,
            'state': state
        }

    def get_template(self, state=None):
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

        return select_template(templates)

    def generate_pdf(self, state=None):
        context = self.get_template_context(state)
        template = self.get_template(state=context['state'])
        file_object = HttpResponse(content_type='application/pdf')

        generate_pdf_template_object(template, file_object, context)

        return file_object

    def generate_html(self, state=None, request=None):
        context = self.get_template_context(state)
        template = self.get_template(state=context['state'])

        return template.render(context, request)

    def _save_pdf(self, state=None):
        file_object = self.generate_pdf(state)

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

    @property
    def entries(self):
        raise NotImplementedError

    @property
    def total(self):
        entries_total = [Decimal(entry.total) for entry in self.entries]
        return sum(entries_total)

    @property
    def total_before_tax(self):
        entries_total = [Decimal(entry.total_before_tax)
                         for entry in self.entries]
        return sum(entries_total)

    @property
    def tax_value(self):
        entries_tax_value = [Decimal(entry.tax_value) for entry in self.entries]
        return sum(entries_tax_value)

    @property
    def total_in_transaction_currency(self):
        entries_total = [Decimal(entry.total_in_transaction_currency)
                         for entry in self.entries]
        return sum(entries_total)

    @property
    def total_before_tax_in_transaction_currency(self):
        entries_total = [Decimal(entry.total_before_tax_in_transaction_currency)
                         for entry in self.entries]
        return sum(entries_total)

    @property
    def tax_value_in_transaction_currency(self):
        entries_tax_value = [Decimal(entry.tax_value_in_transaction_currency)
                             for entry in self.entries]
        return sum(entries_tax_value)
