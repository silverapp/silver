from decimal import Decimal
from datetime import timedelta
from optparse import make_option

from django.core.management.base import BaseCommand
from django.utils import timezone
from dateutil.relativedelta import *

from silver.models import (Customer, MeteredFeatureUnitsLog, Invoice,
                           DocumentEntry, Proforma, Subscription)


class Command(BaseCommand):
    help = 'Generates the billing documents (Invoices, Proformas).'
    option_list = BaseCommand.option_list + (
        make_option('--subscription',
            action='store',
            dest='subscription_id',
            type="int"),
    )

    def _get_proration_percent_and_status(self, subscription, start_date,
                                          end_date):
        """
        Returns proration percent (how much of the interval will be billed) and
        the status (if the subscription is prorated or not).

        :param date: the date at which the percent and status are computed
        :returns: a tuple containing (Decimal(percent), status) where status
            can be one of [True, False]. The decimal value will from the
            interval [0.00; 1.00].
        :rtype: tuple
        """

        intervals = {
            'year': {'years': -subscription.plan.interval_count},
            'month': {'months': -subscription.plan.interval_count},
            'week': {'weeks': -subscription.plan.interval_count},
            'day': {'days': -subscription.plan.interval_count},
        }

        # This will be UTC, which implies a max difference of 27 hours ~= 1 day
        # NOTE (IMPORTANT): this will be a negative interval (e.g.: -1 month,
        # -1 week, etc.)
        interval_len = relativedelta(**intervals[subscription.plan.interval])

        if end_date + interval_len >= start_date:
            # Not prorated
            return False, Decimal('1.00')
        else:
            # Proration
            interval_start = end_date + interval_len
            days_in_interval = (end_date - interval_start).days
            days_since_subscription_start = (end_date - start_date).days
            percent = 100.0 * days_since_subscription_start / days_in_interval
            percent = Decimal(percent).quantize(Decimal('0.00')) / Decimal('100.0')

            return True, percent

    def _add_plan_trial(self, subscription, end_date, invoice=None,
                        proforma=None):
        unit = '%ss' % subscription.plan.interval
        interval = '%sly' % subscription.plan.interval

        start_date = subscription.start_date
        plan_price = Decimal('0.00')

        description = "{plan_name} plan trial subscription ({start_date} -"\
                      " {end_date})".format(plan_name=subscription.plan.name,
                                            interval=interval,
                                            start_date=start_date,
                                            end_date=end_date)
        DocumentEntry.objects.create(
            invoice=invoice, proforma=proforma, description=description,
            unit=unit, unit_price=plan_price, quantity=Decimal('1.00'),
            product_code=subscription.plan.product_code, prorated=prorated,
            start_date=start_date, end_date=end_date
        )

    def _add_plan_entry(self, subscription, now_date, invoice=None,
                  proforma=None):

        unit = '%ss' % subscription.plan.interval
        interval = '%sly' % subscription.plan.interval

        if subscription.is_billed_first_time:
            # First time billing and on trial => add only the trial entry
            if subscription.is_on_trial:
                # Add the trial and exit
                self._add_plan_trial(subscription=subscription,
                                     end_date=now_date, invoice=invoice,
                                     proforma=proforma)
                return
            else:
                # First time billing and with ended trial => 2 entries:
                # 1) The trial one
                # 2) The remaining period

                # Add the trial
                self._add_plan_trial(subscription=subscription,
                                     end_date=subscription.trial_end,
                                     invoice=invoice, proforma=proforma)

                # Add prorated entry with dates between trial_end and now
                # E.g.: start_date = 2015-01-01
                #       trial_end  = 2015-01-10
                #       now_date   = 2015-01-20
                # will generate prorated entry between 2015-01-10 -> 2015-01-20
                # NOTE: even if the subscription was canceled before now_date
                # now_date is still considered the end interval chunk.
                start_date = subscription.trial_end
                end_date = now_date
        else:
            # Was billed before => we use the last_billing_date to determine
            # the current end date
            start_date = subscription.last_billing_date

            if subscription.state == 'canceled':
                end_date = now_date
            else:
                intervals = {
                    'year': {'years': +subscription.plan.interval_count},
                    'month': {'months': +subscription.plan.interval_count},
                    'week': {'weeks': +subscription.plan.interval_count},
                    'day': {'days': +subscription.plan.interval_count},
                }
                interval_len = relativedelta(**intervals[subscription.plan.interval])

                end_date = start_date + interval_len

        prorated, percent = self._get_proration_percent_and_status(
            subscription, start_date, end_date
        )

        # Get the plan's prorated value
        plan_price = subscription.plan.amount * percent

        # E.g.: PlanName monthly plan subscription (2015-01-01 - 2015-02-02)
        description = "{plan_name} {interval} plan subscription ({start_date}"\
                      " - {end_date})".format(plan_name=subscription.plan.name,
                                              interval=interval,
                                              start_date=start_date,
                                              end_date=end_date)

        # Add the document
        DocumentEntry.objects.create(
            invoice=invoice, proforma=proforma, description=description,
            unit=unit, unit_price=plan_price, quantity=Decimal('1.00'),
            product_code=subscription.plan.product_code, prorated=prorated,
            start_date=start_date, end_date=end_date
        )

    def _get_consumed_units(self, included_units, consumed_units):
        if included_units - consumed_units >= 0:
            return 0
        return consumed_units - included_units

    def _get_included_units(self, subscription, metered_feature, now_date):
        if subscription.is_on_trial:
            return metered_feature.included_units

        last_billing_date = subscription.last_billing_date
        if last_billing_date:
            # Was billed before
            start_date = last_billing_date
        else:
            # First billing cycle and the subscription is not on trial
            start_date = subscription.trial_end

        end_date = now_date

        prorated, percent = self._get_proration_percent_and_status(
            subscription, start_date, end_date)

        if not prorated:
            return metered_feature.included_units
        return percent * metered_feature.included_units

    def _add_mf_entries(self, subscription, now_date, invoice=None,
                        proforma=None):
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
                included_units = self._get_included_units(subscription, mf,
                                                          now_date)
                total_units = self._get_consumed_units(included_units,
                                                       log_item.consumed_units)
                unit_price = Decimal('0.00') if subscription.is_on_trial else mf.price_per_unit
                description = "{name} ({start_date} - {end_date})".format(
                    name=mf.name,
                    start_date=log_item.start_date,
                    end_date=log_item.end_date)

                DocumentEntry.objects.create(
                    invoice=invoice, proforma=proforma, description=description,
                    unit=mf.unit, unit_price=unit_price, quantity=total_units,
                    product_code=mf.product_code, start_date=log_item.start_date,
                    end_date=log_item.end_date
                )

    def _add_plan(self, document, subscription, now_date):
        if subscription.plan.provider_flow == 'proforma':
            plan_entry_args = {'proforma': document}
        else:
            plan_entry_args = {'invoice': document}

        plan_entry_args.update({'subscription': subscription,
                                'now_date': now_date})
        self._add_plan_entry(**plan_entry_args)

    def _add_metered_features(self, document, subscription, now_date):
        if subscription.plan.provider_flow == 'proforma':
            mf_entry_args = {'proforma': document}
        else:
            mf_entry_args = {'invoice': document}

        mf_entry_args.update({'subscription': subscription,
                              'now_date': now_date})
        self._add_mf_entries(**mf_entry_args)

    def _create_document(self, provider, customer, subscription, now_date):
        provider_flow = subscription.plan.provider_flow
        DocumentModel = Proforma if provider_flow == 'proforma' else Invoice

        delta = timedelta(days=customer.payment_due_days)
        due_date = now_date + delta
        document = DocumentModel.objects.create(
            provider=subscription.plan.provider, customer=customer,
            due_date=due_date
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

    def _generate_single_document(self, subscription_id):
        subscription = Subscription.objects.get(id=subscription_id)

        provider = subscription.plan.provider
        customer = subscription.customer
        now = timezone.now().date()

        document = self._create_document(provider, customer, subscription, now)
        self._print_status_to_stdout(subscription, created=True)

        # Add plan to invoice/proforma
        self._add_plan(document, subscription, now)
        # Add mf units to proforma/invoice
        self._add_metered_features(document, subscription, now)

        if subscription.state == 'canceled':
            subscription.end()

        if provider.default_document_state == 'issued':
            document.issue()
            document.save()

    def handle(self, *args, **options):
        # Use the same exact date for all the generated documents
        now = timezone.now().date()

        if options['subscription_id']:
            self._generate_single_document(options['subscription_id'])
            return

        for customer in Customer.objects.all():
            if customer.consolidated_billing:
                # Intermediary document for each provider
                document_per_provider = {}

                # Default doc state (issued, draft) for each provider
                default_doc_state = {}

                # TODO:
                # 1) If the subscription was on trial for a part of the month
                # add separate entry for the trial period and a prorated one
                # for the rest of the interval
                # => start_date -> trial_end; trial_end+1 -> now
                # 2) Add separate messages for the trial entry and the normal
                # one

                # Process all the active or canceled subscriptions
                criteria = {'state__in': ['active', 'canceled']}
                for subscription in customer.subscriptions.filter(**criteria):
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
                                                         subscription, now)
                        document_per_provider[provider] = document
                        self._print_status_to_stdout(subscription,
                                                     created=True)

                    # Add plan to invoice/proforma
                    self._add_plan(document, subscription, now)
                    # Add mf units to proforma/invoice
                    self._add_metered_features(document, subscription, now)

                    if subscription.state == 'canceled':
                        subscription.end()
                        subscription.save()

                for provider, document in document_per_provider.iteritems():
                    if default_doc_state[provider] == 'issued':
                        document.issue()
                        document.save()
            else:
                # Generate an invoice for each subscription
                criteria = {'state__in': ['active', 'canceled']}
                for subscription in customer.subscriptions.filter(**criteria):
                    if not subscription.should_be_billed:
                        continue

                    provider = subscription.plan.provider
                    document = self._create_document(provider, customer,
                                                     subscription, now)
                    self._print_status_to_stdout(subscription, created=True)

                    # Add plan to invoice/proforma
                    self._add_plan(document, subscription, now)
                    # Add mf units to proforma/invoice
                    self._add_metered_features(document, subscription, now)

                    if subscription.state == 'canceled':
                        subscription.end()
                        subscription.save()

                    if provider.default_document_state == 'issued':
                        document.issue()
                        document.save()
