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
from datetime import date, datetime
from decimal import Decimal

import pytz
from annoying.functions import get_object_or_None
from django_fsm import (post_transition, TransitionNotAllowed, transition,
                        FSMField)

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.manager import Manager
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.template.loader import select_template
from django.utils.translation import ugettext_lazy as _

from silver.utils.international import currencies
from silver.utils.mail import send_customer_email
from .billing_entities import Customer, Provider


logger = logging.getLogger(__name__)


class PaymentQuerySet(models.QuerySet):
    def _pending_and_unpaid(self):
        return self.filter(status__in=[Payment.Status.Unpaid,
                                       Payment.Status.Pending])

    def due_this_month(self):
        return self._pending_and_unpaid().filter(
            due_date__gte=datetime.now(pytz.utc).date().replace(day=1)
        )

    def due_today(self):
        return self._pending_and_unpaid().filter(
            due_date__exact=datetime.now(pytz.utc).date()
        )

    def overdue(self):
        return self._pending_and_unpaid().filter(
            due_date__lt=datetime.now(pytz.utc).date()
        )

    def overdue_since_last_month(self):
        return self._pending_and_unpaid().filter(
            due_date__lt=datetime.now(pytz.utc).date().replace(day=1)
        )


class Payment(models.Model):
    objects = Manager.from_queryset(PaymentQuerySet)()

    amount = models.DecimalField(
        decimal_places=2, max_digits=8,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    due_date = models.DateField(null=True, blank=True, default=None)

    class Status(object):
        Unpaid = 'unpaid'
        Pending = 'pending'
        Paid = 'paid'
        Canceled = 'canceled'

        FinalStatuses = [Paid, Canceled]

    STATUS_CHOICES = (
        (Status.Unpaid, _('Unpaid')),
        (Status.Pending, _('Pending')),
        (Status.Paid, _('Paid')),
        (Status.Canceled, _('Canceled'))
    )
    status = FSMField(max_length=8, choices=STATUS_CHOICES,
                      default=Status.Unpaid)

    customer = models.ForeignKey(Customer)
    provider = models.ForeignKey(Provider)
    proforma = models.OneToOneField(
        "Proforma",
        null=True, blank=True, related_name='proforma_payment'
    )
    invoice = models.OneToOneField(
        "Invoice",
        null=True, blank=True, related_name='invoice_payment'
    )
    visible = models.BooleanField(default=True)
    currency = models.CharField(
        choices=currencies, max_length=4, default='USD',
        help_text='The currency used for billing.'
    )
    currency_rate_date = models.DateField(blank=True, null=True)

    @transition(field='status',
                source=[Status.Unpaid, Status.Pending],
                target=Status.Canceled)
    def cancel(self):
        pass

    @transition(field='status',
                source=Status.Unpaid, target=Status.Pending)
    def process(self):
        pass

    @transition(field='status',
                source=(Status.Unpaid, Status.Pending),
                target=Status.Paid)
    def succeed(self):
        pass

    @transition(field='status',
                source=Status.Pending, target=Status.Unpaid)
    def fail(self):
        pass

    def clean(self):
        document = self.invoice or self.proforma
        if document:
            if document.provider != self.provider:
                raise ValidationError(
                    'Provider doesn\'t match with the one in documents.'
                )

            if document.customer != self.customer:
                raise ValidationError(
                    'Customer doesn\'t match with the one in documents.'
                )

        if self.invoice and self.proforma:
            if self.invoice.proforma != self.proforma:
                raise ValidationError('Invoice and proforma are not related.')

    def _log_unsuccessful_transition(self, transition_name):
        logger.warning('[Models][Payment]: %s', {
            'detail': 'Couldn\'t %s payment' % transition_name,
            'payment_id': self.id,
            'customer_id': self.customer.id
        })

    @property
    def is_overdue(self):
        if self.status == Payment.Status.Unpaid and self.days_left <= 0:
            return True

        return False

    @property
    def days_left(self):
        return (self.due_date - date.today()).days

    def __unicode__(self):
        return '#%0#5d' % self.pk

    def diff(self, other_payment):
        changes = {}
        for attr in ['amount', 'due_date', 'status', 'customer', 'provider',
                     'proforma', 'invoice', 'visible', 'currency',
                     'currency_rate_date']:
            if not hasattr(other_payment, attr) or not hasattr(self, attr):
                continue

            current = getattr(self, attr, None)
            other = getattr(other_payment, attr, None)

            if current != other:
                changes[attr] = {
                    'from': current,
                    'to': other
                }

        return changes


def send_new_payment_email(payment):
    subject = u'New {} payment'.format(payment.provider.name)

    templates = [
        'payments/{}/new_payment_email.html'.format(payment.provider.slug),
        'payments/new_payment_email.html'
    ]

    template = select_template(templates)
    body = template.render({
        'payment': payment,
        'customer': payment.customer,
    })

    from_email = payment.provider.display_email

    send_customer_email(payment.customer, subject=subject, body=body,
                        from_email=from_email)


def send_payment_processing_email(payment):
    subject = u'{} payment being processed'.format(payment.provider.name)

    templates = [
        'payments/{}/payment_processing_email.html'.format(
            payment.provider.slug
        ),
        'payments/payment_processing_email.html'
    ]

    template = select_template(templates)
    body = template.render({
        'payment': payment,
        'customer': payment.customer,
    })

    from_email = payment.provider.display_email

    send_customer_email(payment.customer, subject=subject, body=body,
                        from_email=from_email)


def send_payment_paid_email(payment):
    subject = u'{} payment successful'.format(payment.provider.name)

    templates = [
        'payments/{}/payment_paid_email.html'.format(payment.provider.slug),
        'payments/payment_paid_email.html'
    ]

    template = select_template(templates)
    body = template.render({
        'payment': payment,
        'customer': payment.customer,
    })

    from_email = payment.provider.display_email

    send_customer_email(payment.customer, subject=subject, body=body,
                        from_email=from_email)


@receiver(pre_save, sender=Payment)
def pre_payment_save(sender, instance=None, **kwargs):
    old = get_object_or_None(Payment, pk=instance.pk)
    setattr(instance, 'old_value', old)


@receiver(post_save, sender=Payment)
def post_payment_save(sender, instance, **kwargs):
    if not instance.old_value:
        logger.info('[Models][Payment]: %s', {
            'detail': 'A payment was created.',
            'payment_id': instance.id,
            'customer_id': instance.customer.id,
            'invoice_id': instance.invoice.id if instance.invoice else None,
            'proforma_id':
                instance.proforma.id if instance.proforma else None
        })

    if instance.old_value:
        changes = instance.diff(instance.old_value)

        if ('visible' in changes and
                not changes['visible']['from'] and
                changes['visible']['to']):
            send_new_payment_email(instance)
    elif instance.visible and \
            instance.status not in [Payment.Status.Paid,
                                    Payment.Status.Canceled]:
        send_new_payment_email(instance)


@receiver(post_transition)
def post_transition_callback(sender, instance, name, source, target, **kwargs):
    """
    Syncs the related documents of a payment state with the payment status
    """
    if issubclass(sender, Payment):
        if target == Payment.Status.Paid:
            send_mail = False

            if instance.proforma and \
                    instance.proforma.state != instance.proforma.STATES.PAID:
                try:
                    instance.proforma.pay()
                    instance.proforma.save()

                    send_mail = True
                except TransitionNotAllowed:
                    logger.warning('[Models][Payment]: %s', {
                        'detail': 'Couldn\'t automatically pay proforma.',
                        'payment_id': instance.id,
                        'payment_status': instance.status,
                        'proforma_id': instance.proforma.id,
                        'proforma_status': instance.proforma.state
                    })

            if instance.invoice and \
                    instance.invoice.state != instance.invoice.STATES.PAID:
                try:
                    instance.invoice.pay()
                    instance.invoice.save()

                    send_mail = True
                except TransitionNotAllowed:
                    logger.warning('[Models][Payment]: %s', {
                        'detail': 'Couldn\'t automatically pay invoice.',
                        'payment_id': instance.id,
                        'payment_status': instance.status,
                        'invoice_id': instance.invoice.id,
                        'invoice_status': instance.invoice.state
                    })

            if send_mail:
                send_payment_paid_email(instance)
