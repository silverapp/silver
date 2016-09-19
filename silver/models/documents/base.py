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

from django_fsm import TransitionNotAllowed, FSMField, transition
from django_fsm import post_transition
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
from django.dispatch import receiver
from django.http import HttpResponse
from django.template.loader import select_template
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _
from django.utils.module_loading import import_string


from .entries import DocumentEntry
from silver.models.billing_entities import Customer, Provider
from silver.models.payments import Payment

from silver.utils.international import currencies


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
        help_text='The currency used for billing.'
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
        super(BillingDocument, self).__init__(*args, **kwargs)
        self._last_state = self.state

    @property
    def payment(self):
        raise NotImplementedError

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
            entry_clone = entry.clone()
            document_type_name = self.__class__.__name__.lower()
            setattr(entry_clone, document_type_name, clone)
            entry_clone.save()

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

    @property
    def fields_for_payment_creation(self):
        fields = {
            'customer': self.customer,
            'provider': self.provider,
            'due_date': self.due_date,
            'amount': self.total,
            'currency': self.currency,
            'visible': (self.state in [BillingDocument.STATES.ISSUED,
                                       BillingDocument.STATES.PAID]),
            'currency_rate_date': timezone.now().date(),
            'status': (Payment.Status.Unpaid if self.total else
                       Payment.Status.Paid),
        }

        return fields

    def create_payment(self):
        fields = self.fields_for_payment_creation

        return Payment.objects.create(**fields)


@receiver(post_transition)
def post_transition_callback(sender, instance, name, source, target, **kwargs):
    if isinstance(instance, BillingDocument):
        if target == BillingDocument.STATES.ISSUED:
            if not instance.payment:
                if instance.related_document and \
                        instance.related_document.payment:
                    payment = instance.related_document.payment

                    document_type_name = instance.__class__.__name__.lower()
                    setattr(payment, document_type_name, instance)
                    payment.save()
                else:
                    payment = instance.create_payment()

                    logger.info('[Models][Documents]: %s', {
                        'detail': 'Payment automatically created for document.',
                        'payment_id': payment.id,
                        'customer_id': payment.customer.id,
                        'document_id': instance.id,
                        'document_type': sender.kind,
                        'document_state': target
                    })
            else:
                if not instance.payment.visible:
                    instance.payment.visible = True
                    instance.payment.save()
        elif target == BillingDocument.STATES.CANCELED:
            if instance.payment:
                try:
                    instance.payment.cancel()
                    instance.payment.save()
                except TransitionNotAllowed:
                    pass
