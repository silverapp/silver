from decimal import Decimal
from django.core.management.base import BaseCommand

from silver.models import (Customer, MeteredFeatureUnitsLog, Invoice,
                           DocumentEntry, Proforma)

class Command(BaseCommand):

    def _add_plan_document_entry(self, subscription, plan, invoice=None,
                                 proforma=None):

        description = subscription.description or '%s plan subscription.' % plan.name
        DocumentEntry.objects.create(invoice=invoice, proforma=proforma,
                                     description=description,
                                     unit_price=plan.amount,
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
                # Add the metered feature to the invoice
                DocumentEntry.objects.create(invoice=invoice,
                                             proforma=proforma,
                                             description=mf.name,
                                             unit_price=mf.price_per_unit,
                                             quantity=final_units_count,
                                             product_code=mf.product_code)

    def _add_plan_entry(self, provider_flow, subscription, plan, document):
        if provider_flow == 'proforma':
            entry_args = {'proforma': document}
        else:
            entry_args = {'invoice': document}

        doc_entry_args = entry_args.copy()
        doc_entry_args.update({'subscription': subscription,
                               'plan': plan})
        self._add_plan_document_entry(**doc_entry_args)

    def _add_mf_entries(self, provider_flow, document, subscription):
        if provider_flow == 'proforma':
            entry_args = {'proforma': document}
        else:
            entry_args = {'invoice': document}

        mf_entry_args = entry_args.copy()
        mf_entry_args.update({'subscription': subscription})
        self._add_mf_document_entries(**mf_entry_args)

    def handle(self, *args, **kwargs):
        for customer in Customer.objects.all():
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
                        document = DocumentModel.objects.create(
                            provider=plan.provider, customer=customer)
                        document_per_provider[plan.provider] = document

                    # Add plan to invoice/proforma
                    self._add_plan_entry(provider_flow, subscription, plan,
                                         document)
                    # Add mf units to proforma/invoice
                    self._add_mf_entries(provider_flow, document, subscription)
            else:
                # Generate an invoice for each subscription
                for subscription in customer.subscriptions.all():
                    provider_flow = subscription.plan.provider_flow
                    DocumentModel = Proforma if provider_flow == 'proforma' else Invoice

                    plan = subscription.plan
                    document = DocumentModel.objects.create(
                        provider=plan.provider, customer=customer)

                    # Add plan to invoice/proforma
                    self._add_plan_entry(provider_flow, subscription, plan,
                                         document)
                    # Add mf units to proforma/invoice
                    self._add_mf_entries(provider_flow, document, subscription)
