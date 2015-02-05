from decimal import Decimal
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from silver.models import (Customer, MeteredFeatureUnitsLog, Invoice,
                           DocumentEntry, Proforma)

class Command(BaseCommand):
    help = 'Generates the billing documents (Invoices, Proformas).'

    def _add_plan_document_entry(self, subscription, plan, invoice=None,
                                 proforma=None):
        description = subscription.description or '%s plan subscription.' % plan.name

        unit_price = Decimal('0.00') if subscription.on_trial else plan.amount
        DocumentEntry.objects.create(invoice=invoice, proforma=proforma,
                                     description=description,
                                     subscription=subscription,
                                     unit_price=unit_price,
                                     quantity=Decimal('1.00'),
                                     product_code=plan.product_code)

    def _add_mf_document_entries(self, subscription, invoice=None,
                                 proforma=None):
        for mf in subscription.plan.metered_features.all():
            criteria = {'metered_feature': mf,
                        'subscription': subscription}
            total_units_consumed = 0
            # Filter the ones included in the interval and for each separate
            # entry (differente start_date, end_date) add a new document entry
            consumed_mf_log = MeteredFeatureUnitsLog.objects.filter(**criteria)
            for log_item in consumed_mf_log:
                total_units_consumed += log_item.consumed_units
            final_units_count = max(0, total_units_consumed - mf.included_units)
            unit_price = Decimal('0.00') if subscription.on_trial else mf.price_per_unit
            # Add the metered feature to the invoice
            DocumentEntry.objects.create(invoice=invoice,
                                         proforma=proforma,
                                         description=mf.name,
                                         unit_price=unit_price,
                                         quantity=final_units_count,
                                         product_code=mf.product_code)

    def _add_plan_entry(self, subscription, plan, document):
        provider_flow = subscription.plan.provider_flow
        if provider_flow == 'proforma':
            entry_args = {'proforma': document}
        else:
            entry_args = {'invoice': document}

        doc_entry_args = entry_args.copy()
        doc_entry_args.update({'subscription': subscription, 'plan': plan})
        self._add_plan_document_entry(**doc_entry_args)

    def _add_mf_entries(self, document, subscription):
        provider_flow = subscription.plan.provider_flow
        if provider_flow == 'proforma':
            entry_args = {'proforma': document}
        else:
            entry_args = {'invoice': document}

        mf_entry_args = entry_args.copy()
        mf_entry_args.update({'subscription': subscription})
        self._add_mf_document_entries(**mf_entry_args)

    def _create_document(provider, customer, subscription):
        provider_flow = subscription.plan.provider_flow
        DocumentModel = Proforma if provider_flow == 'proforma' else Invoice

        delta = timedelta(days=customer.payment_due_days)
        due_date = timezone.now().date() + delta
        document = DocumentModel.objects.create(
            provider=subscription.plan.provider, customer=customer,
            due_date=due_date, subscription=subscription)

        return document

    def handle(self, *args, **options):
        for customer in Customer.objects.all():
            self.stdout.write('Generating invoice(s) for: %s' % customer)
            if customer.consolidated_billing:
                # Cache the invoice/proforma per provider
                document_per_provider = {}

                # Save the default used state for each provider
                default_doc_state = {}

                for subscription in customer.subscriptions.all():
                    if not subscription.should_be_billed:
                        continue

                    plan = subscription.plan

                    default_doc_state[plan.provider] = plan.provider.default_document_state
                    if plan.provider in document_per_provider:
                        document = document_per_provider[plan.provider]
                    else:
                        document = self._create_document(
                            plan.provider, customer, subscription)
                        document_per_provider[plan.provider] = document

                    # Add plan to invoice/proforma
                    self._add_plan_entry(subscription, plan, document)
                    # Add mf units to proforma/invoice
                    self._add_mf_entries(document, subscription)

                for provider, document in document_per_provider.iteritems():
                    if default_doc_state[provider] == 'issued':
                        document.issue()
                        document.save()
            else:
                # Generate an invoice for each subscription
                for subscription in customer.subscriptions.all():
                    if not subscription.should_be_billed:
                        continue

                    plan = subscription.plan
                    document = self._create_document(plan.provider, customer,
                                                     subscription)

                    # Add plan to invoice/proforma
                    self._add_plan_entry(subscription, plan, document)
                    # Add mf units to proforma/invoice
                    self._add_mf_entries(document, subscription)

                    if plan.provider.default_document_state == 'issued':
                        document.issue()
                        document.save()
