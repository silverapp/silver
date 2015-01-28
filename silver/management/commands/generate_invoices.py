from decimal import Decimal
from django.core.management.base import BaseCommand

from silver.models import (Customer, MeteredFeatureUnitsLog, Invoice,
                           DocumentEntry)

class Command(BaseCommand):

    def handle(self, *args, **kwargs):
        for customer in Customer.objects.all():
            if customer.consolidated_billing:
                # For now we take into consideration only the invoices
                # we will deal with the proformas later.
                invoice_per_provider = {}
                for subscription in customer.subscriptions.all():
                    plan = subscription.plan
                    if plan.provider in invoice_per_provider:
                        invoice = invoice_per_provider[plan.provider]
                    else:
                        invoice = Invoice.objects.create(provider=plan.provider,
                                                         customer=customer)
                        invoice_per_provider[plan.provider] = invoice

                    # TODO: Add description field to Subscription and here
                    # use either the subscription.description or plan.name
                    DocumentEntry.objects.create(invoice=invoice,
                                                 description=plan.name,  # TODO
                                                 unit_price=plan.amount,
                                                 quantity=Decimal(1),
                                                 product_code=plan.product_code)
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
                                                         description=mf.name,
                                                         unit_price=mf.price_per_unit,
                                                         quantity=final_units_count,
                                                         product_code=mf.product_code)
            else:
                # Generate an invoice for each subscription
                for subscription in customer.subscriptions.all():
                    plan = subscription.plan
                    invoice = Invoice.objects.create(provider=plan.provider,
                                                    customer=customer)

                    # TODO: Add description field to Subscription and here
                    # use either the subscription.description or plan.name
                    DocumentEntry.objects.create(invoice=invoice,
                                                 description=plan.name,  # TODO
                                                 unit_price=plan.amount,
                                                 quantity=Decimal(1),
                                                 product_code=plan.product_code)
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
                                                         description=mf.name,
                                                         unit_price=mf.price_per_unit,
                                                         quantity=final_units_count,
                                                         product_code=mf.product_code)

