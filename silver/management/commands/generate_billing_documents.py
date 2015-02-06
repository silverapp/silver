from decimal import Decimal
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from dateutil.relativedelta import *

from silver.models import (Customer, MeteredFeatureUnitsLog, Invoice,
                           DocumentEntry, Proforma)

class Command(BaseCommand):
    help = 'Generates the billing documents (Invoices, Proformas).'

    def _get_plan_price(self, subscription):
        now = timezone.now().date()
        intervals = {
            'year': {'years': -subscription.plan.interval_count},
            'month': {'month': -subscription.plan.interval_count},
            'week': {'wee': -subscription.plan.interval_count},
            'day': {'day': -subscription.plan.interval_count},
        }
        # This will be UTC, which implies a max difference of 27 hours ~= 1 day
        interval_len = relativedelta(**intervals[subscription.plan.interval])

        if subscription.last_billing_date:
            # Full interval value
            return subscription.plan.amount, False
        else:
            # Proration
            days_in_interval = (now - (now + interval_len)).days
            days_since_subscription_start = (now - subscription.start_date).days
            percent = 100.0 * days_since_subscription_start / days_in_interval
            return Decimal(percent) * subscription.plan.amount, True

    def _add_plan(self, subscription, invoice=None, proforma=None):
        interval = '%sly' % subscription.plan.interval

        if not subscription.last_billing_date:
            # First time bill
            start_date = subscription.start_date
            end_date = timzone.now().date()
        else:
            intervals = {
                'year': {'years': subscription.plan.interval_count},
                'month': {'month': subscription.plan.interval_count},
                'week': {'wee': subscription.plan.interval_count},
                'day': {'day': subscription.plan.interval_count},
            }
            interval_len = relativedelta(**intervals[subscription.plan.interval])

            start_date = subscription.last_billing_date
            end_date = subscription.last_billing_date + interval_len

        composed_description = "{plan_name} {interval} plan subscription"\
                               " ({start_date} - {end_date})".format(
                                    plan_name=subscription.plan.name,
                                    interval=interval, start_date=start_date,
                                    end_date=end_date)
        description = subscription.description or composed_description


        if not subscription.on_trial:
            unit_price, prorated = self._get_price()
        else:
            unit_price, prorated = Decimal('0.00'), False

        unit = '%ss' % subscription.plan.interval
        DocumentEntry.objects.create(
            invoice=invoice, proforma=proforma, description=description,
            unit=unit, unit_price=unit_price, quantity=Decimal('1.00'),
            product_code=subscription.plan.product_code, prorated=prorated,
            start_date=start_date, end_date=end_date
        )

    def _add_metered_features(self, subscription, invoice=None, proforma=None):
        if subscription.last_billing_date:
            start_date = subscription.last_billing_date
        else:
            start_date = subscription.start_date

        for mf in subscription.plan.metered_features.all():
            criteria = {
                'metered_feature': mf,
                'subscription': subscription,
                'start_date__gte': start_date,
            }

            consumed_mf_log = MeteredFeatureUnitsLog.objects.filter(**criteria)
            for log_item in consumed_mf_log:
                total_units = max(0, log_item.consumed_units - mf.included_units)
                unit_price = Decimal('0.00') if subscription.on_trial else mf.price_per_unit
                DocumentEntry.objects.create(
                    invoice=invoice, proforma=proforma, description=mf.name,
                    unit=mf.unit, unit_price=unit_price, quantity=total_units,
                    product_code=mf.product_code
                )

    def _add_plan_entry(self, document, subscription):
        if subscription.plan.provider_flow == 'proforma':
            plan_entry_args = {'proforma': document}
        else:
            plan_entry_args = {'invoice': document}

        plan_entry_args.update({'subscription': subscription})
        self._add_plan(**plan_entry_args)

    def _add_mf_entries(self, document, subscription):
        if subscription.plan.provider_flow == 'proforma':
            mf_entry_args = {'proforma': document}
        else:
            mf_entry_args = {'invoice': document}

        mf_entry_args.update({'subscription': subscription})
        self._add_metered_features(**mf_entry_args)

    def _create_document(self, provider, customer, subscription):
        provider_flow = subscription.plan.provider_flow
        DocumentModel = Proforma if provider_flow == 'proforma' else Invoice

        delta = timedelta(days=customer.payment_due_days)
        due_date = timezone.now().date() + delta
        document = DocumentModel.objects.create(
            provider=subscription.plan.provider, customer=customer,
            due_date=due_date, subscription=subscription
        )

        return document

    def _print_status_to_stdout(self, subscription, created=False):
        if subscription.plan.provider_flow == 'proforma':
            doc_name = 'Proforma'
        else:
            doc_name = 'Invoice'
        action = 'Generating' if created else 'Updating'
        msg = '{action} {doc_name} for {subscription}.'.format(
            action=action, doc_name=doc_name, subscription=subscription)

        self.stdout.write(msg)


    def handle(self, *args, **options):
        for customer in Customer.objects.all():
            if customer.consolidated_billing:

                # Intermediary document for each provider
                document_per_provider = {}

                # Default doc state (issued, draft) for each provider
                default_doc_state = {}

                for subscription in customer.subscriptions.all():
                    if not subscription.should_be_billed:
                        continue

                    provider = subscription.plan.provider

                    default_doc_state[provider] = provider.default_document_state
                    if provider in document_per_provider:
                        document = document_per_provider[provider]
                        self._print_status_to_stdout(subscription,
                                                     created=False)
                    else:
                        document = self._create_document(provider, customer,
                                                         subscription)
                        document_per_provider[provider] = document
                        self._print_status_to_stdout(subscription,
                                                     created=True)

                    # Add plan to invoice/proforma
                    self._add_plan_entry(document, subscription)
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

                    provider = subscription.plan.provider
                    document = self._create_document(provider, customer,
                                                     subscription)
                    self._print_status_to_stdout(subscription, created=True)

                    # Add plan to invoice/proforma
                    self._add_plan_entry(document, subscription)
                    # Add mf units to proforma/invoice
                    self._add_mf_entries(document, subscription)

                    if provider.default_document_state == 'issued':
                        document.issue()
                        document.save()
