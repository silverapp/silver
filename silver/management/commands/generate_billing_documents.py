from decimal import Decimal
from datetime import timedelta
from optparse import make_option

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings

from silver.models import (Customer, MeteredFeatureUnitsLog, Invoice,
                           DocumentEntry, Proforma)

class Command(BaseCommand):
    help = 'Generates the billing documents (Invoices, Proformas).'
    option_list = BaseCommand.option_list + (
        make_option('--state',
                    action='store',
                    dest='state',
                    type='string',
                    default='draft',
                    help='The final state for the generated documents'),
    )

    def _add_plan_document_entry(self, subscription, plan, invoice=None,
                                 proforma=None):

        description = subscription.description or '%s plan subscription.' % plan.name

        unit_price = Decimal('0.00') if subscription.on_trial else plan.amount
        DocumentEntry.objects.create(invoice=invoice, proforma=proforma,
                                     description=description,
                                     unit_price=unit_price,
                                     quantity=Decimal('1.00'),
                                     product_code=plan.product_code)

    def _add_mf_document_entries(self, subscription, invoice=None,
                                 proforma=None):

        for mf in subscription.plan.metered_features.all():
            criteria = {'metered_feature': mf,
                        'subscription': subscription}
            total_units_consumed = 0
            consumed_mf_log = MeteredFeatureUnitsLog.objects.filter(**criteria)
            for log_item in consumed_mf_log:
                total_units_consumed += log_item.consumed_units
            final_units_count = max(0, total_units_consumed - mf.included_units)
            if final_units_count != 0:
                unit_price = Decimal('0.00') if subscription.on_trial else mf.price_per_unit
                # Add the metered feature to the invoice
                DocumentEntry.objects.create(invoice=invoice,
                                             proforma=proforma,
                                             description=mf.name,
                                             unit_price=unit_price,
                                             quantity=final_units_count,
                                             product_code=mf.product_code)

    def _add_plan_entry(self, provider_flow, subscription, plan, document):
        if provider_flow == 'proforma':
            entry_args = {'proforma': document}
        else:
            entry_args = {'invoice': document}

        doc_entry_args = entry_args.copy()
        doc_entry_args.update({'subscription': subscription, 'plan': plan})
        self._add_plan_document_entry(**doc_entry_args)

    def _add_mf_entries(self, provider_flow, document, subscription):
        if provider_flow == 'proforma':
            entry_args = {'proforma': document}
        else:
            entry_args = {'invoice': document}

        mf_entry_args = entry_args.copy()
        mf_entry_args.update({'subscription': subscription})
        self._add_mf_document_entries(**mf_entry_args)

    def handle(self, *args, **options):
        final_state = options['state']
        for customer in Customer.objects.all():
            self.stdout.write('Generating invoice(s) for: %s' % customer)
            if customer.consolidated_billing:
                # Cache the invoice/proforma per provider
                document_per_provider = {}
                for subscription in customer.subscriptions.all():
                    provider_flow = subscription.plan.provider_flow
                    DocumentModel = Proforma if provider_flow == 'proforma' else Invoice

                    plan = subscription.plan
                    if plan.provider in document_per_provider:
                        document = document_per_provider[plan.provider]
                    else:
                        delta = timedelta(days=settings.PAYMENT_DUE_DAYS)
                        due_date = timezone.now().date() + delta
                        document = DocumentModel.objects.create(
                            provider=plan.provider, customer=customer,
                            due_date=due_date)
                        document_per_provider[plan.provider] = document

                    # Add plan to invoice/proforma
                    self._add_plan_entry(provider_flow, subscription, plan,
                                         document)
                    # Add mf units to proforma/invoice
                    self._add_mf_entries(provider_flow, document, subscription)

                    if final_state == 'issued':
                        for document in document_per_provider.values():
                            document.issue()
                            document.save()
            else:
                # Generate an invoice for each subscription
                for subscription in customer.subscriptions.all():
                    provider_flow = subscription.plan.provider_flow
                    DocumentModel = Proforma if provider_flow == 'proforma' else Invoice

                    plan = subscription.plan
                    delta = timedelta(days=settings.PAYMENT_DUE_DAYS)
                    due_date = timezone.now().date() + delta
                    document = DocumentModel.objects.create(
                        provider=plan.provider, customer=customer,
                        due_date=due_date)

                    # Add plan to invoice/proforma
                    self._add_plan_entry(provider_flow, subscription, plan,
                                         document)
                    # Add mf units to proforma/invoice
                    self._add_mf_entries(provider_flow, document, subscription)

                    if final_state == 'issued':
                        for document in document_per_provider.values():
                            document.issue()
                            document.save()
