# Copyright (c) 2015 Presslabs SRL
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

from __future__ import absolute_import

import datetime as dt
import logging
from collections import defaultdict
from dataclasses import dataclass

from decimal import Decimal
from fractions import Fraction
from typing import Tuple, Dict, List, Union

from django.utils import timezone

from silver.models import (
    Customer, Subscription, Proforma, Invoice, Provider, BillingLog, DocumentEntry, Plan
)
from silver.models.discounts import Discount
from silver.models.documents.entries import OriginType, EntryInfo
from silver.utils.dates import ONE_DAY
from silver.utils.numbers import quantize_fraction

logger = logging.getLogger(__name__)


@dataclass
class DiscountInfo:
    discount: 'silver.models.Discount'
    applies_to_all_discountable_entries_in_interval: bool
    matching_subscriptions: List['silver.models.Subscription']


class DocumentsGenerator(object):
    def generate(self, subscription=None, billing_date=None, customers=None,
                 force_generate=False):
        """
        The `public` method called when one wants to generate the billing documents.

        :param subscription: the subscription for which one wants to generate the
            proformas/invoices.
        :param billing_date: the date used as billing date
        :param customers: the customers for which one wants to generate the
            proformas/invoices.
        :param force_generate: if True, invoices are generated at the date
            indicated by `billing_date` instead of the normal end of billing
            cycle.

        :note
                If `subscription` is passed, only the documents for that subscription are
            generated.
                If the `customers` parameter is passed, only the docments for those customers are
            generated.
                Only one of the `customers` and `subscription` parameters may be passed at a time.
                If neither the `subscription` nor the `customers` parameters are passed, the
                documents for all the customers will be generated.
        """

        if not subscription:
            customers = customers or Customer.objects.all()
            self._generate_all(billing_date=billing_date,
                               customers=customers,
                               force_generate=force_generate)
        else:
            self._generate_for_single_subscription(subscription=subscription,
                                                   billing_date=billing_date,
                                                   force_generate=force_generate)

    def _generate_all(self, billing_date=None, customers=None, force_generate=False):
        """
        Generates the invoices/proformas for all the subscriptions that should
        be billed.
        """

        billing_date = billing_date or timezone.now().date()
        # billing_date -> the date when the billing documents are issued.

        for customer in customers:
            if customer.consolidated_billing:
                self._generate_for_user_with_consolidated_billing(
                    customer, billing_date, force_generate
                )
            else:
                self._generate_for_user_without_consolidated_billing(
                    customer, billing_date, force_generate
                )

    def _log_subscription_billing(self, document, subscription):
        logger.debug('Billing subscription: %s', {
            'subscription': subscription.id,
            'state': subscription.state,
            'doc_type': document.provider.flow,
            'number': document.number,
            'provider': document.provider.id,
            'customer': document.customer.id
        })

    def get_subscriptions_prepared_for_billing(self, customer, billing_date, force_generate):
        # Select all the active or canceled subscriptions
        subs_to_bill = []
        criteria = {'state__in': [Subscription.STATES.ACTIVE,
                                  Subscription.STATES.CANCELED]}
        for subscription in customer.subscriptions.filter(**criteria):
            if subscription.should_be_billed(billing_date) or force_generate:
                subs_to_bill.append(subscription)

        return subs_to_bill

    def _bill_subscription_into_document(self, subscription, billing_date, document=None) \
            -> Tuple[Union[Invoice, Proforma], List[EntryInfo]]:
        if not document:
            document = self._create_document(subscription, billing_date)

        self._log_subscription_billing(document, subscription)

        kwargs = subscription.billed_up_to_dates

        kwargs.update({
            'billing_date': billing_date,
            'subscription': subscription,
            subscription.provider.flow: document,
        })

        billing_log, entries_info = self.add_subscription_cycles_to_document(**kwargs)

        if subscription.state == Subscription.STATES.CANCELED:
            subscription.end()
            subscription.save()

        return document, entries_info

    def _create_discount_entries(self, entries_info: List[EntryInfo], invoice=None, proforma=None):
        subscriptions = set([entry.subscription for entry in entries_info])

        discounts = {}
        for subscription in subscriptions:
            sub_discounts = Discount.for_subscription(subscription).filter(
                state=Discount.STATES.ACTIVE
            )

            for discount in sub_discounts:
                if discount.id not in discounts:
                    discount.matching_subscriptions = [subscription]
                    discounts[discount.id] = discount
                else:
                    discounts[discount.id].matching_subscriptions.append(subscription)

        # group entries_info by start_date - end_date intervals
        entries_by_interval = defaultdict(lambda: [])
        for entry_info in entries_info:
            entries_by_interval[(entry_info.start_date, entry_info.end_date)].append(entry_info)

        # create discounts separated by billing intervals
        discount_entries = []

        for interval, entries in entries_by_interval.items():
            discount_entries += self._create_discount_entries_by_interval(
                list(discounts.values()), interval, entries,
                invoice=invoice, proforma=proforma
            )

        return discount_entries

    def _create_discount_entries_by_interval(
        self, matching_discounts, interval, entries_info, invoice=None, proforma=None
    ):
        discounts_affecting_plan = Discount.filter_discounts_affecting_plan(matching_discounts)
        discounts_affecting_metered_features = \
            Discount.filter_discounts_affecting_metered_features(matching_discounts)

        discount_to_entries: Dict[Discount, List[EntryInfo]] = defaultdict(lambda: [])
        entry_to_discounts: Dict[EntryInfo, List[Discount]] = defaultdict(lambda: [])

        provider = entries_info[0].subscription.provider
        customer = entries_info[0].subscription.customer
        start_date = interval[0]
        end_date = interval[1]

        discount_infos = {
            discount: DiscountInfo(
                discount=discount,
                applies_to_all_discountable_entries_in_interval=False,
                matching_subscriptions=discount.matching_subscriptions,
            )
            for discount in matching_discounts
        }

        for entry_info in entries_info:
            if entry_info.origin_type == OriginType.Plan:
                for discount in discounts_affecting_plan:
                    if entry_info.subscription not in discount.matching_subscriptions:
                        continue

                    discount_to_entries[discount].append(entry_info)
                    entry_to_discounts[entry_info].append(discount)
            elif entry_info.origin_type == OriginType.MeteredFeature:
                for discount in discounts_affecting_metered_features:
                    if entry_info.subscription not in discount.matching_subscriptions:
                        continue

                    discount_to_entries[discount].append(entry_info)
                    entry_to_discounts[entry_info].append(discount)

        discounts = defaultdict(lambda: Decimal(0.0))

        for discount, entries in discount_to_entries.items():
            if len(entries) == len(entries_info):
                discount_infos[discount].applies_to_all_discountable_entries_in_interval = True

            for entry in entries:
                proration_fraction, _ = discount.proration_fraction(
                    entry.subscription, start_date, end_date, entry.origin_type
                )

                discounts[discount] += quantize_fraction(
                    Fraction(str(discount.as_additive)) * Fraction(str(entry.amount)) * proration_fraction
                )

        max_noncumulative_discount_per_document = Decimal(0.0)
        noncumulative_discount_per_document = None
        for discount in Discount.filter_noncumulative(discounts):
            amount = discounts[discount]
            if amount > max_noncumulative_discount_per_document:
                max_noncumulative_discount_per_document = amount
                noncumulative_discount_per_document = discount

        additive_discounts = {}
        for discount in Discount.filter_additive(discounts):
            additive_discounts[discount] = discounts[discount]

        extra_context = {
            'start_date': start_date,
            'end_date': end_date,
            'context': 'discount',
        }

        if max_noncumulative_discount_per_document > sum(additive_discounts.values()):
            extra_context['subscriptions'] = set(
                entry.subscription
                for entry in discount_to_entries[noncumulative_discount_per_document]
            )
            extra_context['discount_info'] = discount_infos[noncumulative_discount_per_document]

            description = noncumulative_discount_per_document._entry_description(
                provider, customer, extra_context
            )

            return [
                DocumentEntry.objects.create(
                    invoice=invoice, proforma=proforma, description=description,
                    unit_price=-max_noncumulative_discount_per_document, quantity=Decimal('1.00'),
                    product_code=noncumulative_discount_per_document.product_code,
                    start_date=start_date, end_date=end_date,
                )
            ]

        entries = []
        for discount, amount in additive_discounts.items():
            if amount <= 0:
                continue

            context = extra_context.copy()
            context['subscriptions'] = set(
                entry.subscription for entry in discount_to_entries[discount]
            )
            context['discount_info'] = discount_infos[discount]

            entries.append(DocumentEntry.objects.create(
                invoice=invoice, proforma=proforma,
                description=discount._entry_description(provider, customer, context),
                unit_price=-amount, quantity=Decimal('1.00'),
                product_code=discount.product_code,
                start_date=start_date, end_date=end_date,
            ))

        return entries

    def _generate_for_user_with_consolidated_billing(self, customer, billing_date, force_generate):
        """
        Generates the billing documents for all the subscriptions of a customer
        who uses consolidated billing.
        """

        # For each provider there will be one invoice or proforma. The cache is necessary as a
        # certain customer might have more than one subscription
        # => all the subscriptions belonging to the same provider will be added to the same document

        existing_provider_documents = {}
        merged_entries_per_provider = defaultdict(lambda: [])

        for subscription in self.get_subscriptions_prepared_for_billing(customer, billing_date,
                                                                        force_generate):
            provider = subscription.plan.provider

            existing_document = existing_provider_documents.get(provider)

            existing_provider_documents[provider], entries_info = self._bill_subscription_into_document(
                subscription, billing_date, document=existing_document
            )

            merged_entries_per_provider[provider] += entries_info

        for provider, document in existing_provider_documents.items():
            kwargs = {'entries_info': merged_entries_per_provider[provider],
                      provider.flow: document}

            self._create_discount_entries(**kwargs)

            if provider.default_document_state == Provider.DEFAULT_DOC_STATE.ISSUED:
                document.issue()

    def _generate_for_user_without_consolidated_billing(self, customer, billing_date,
                                                        force_generate):
        """
        Generates the billing documents for all the subscriptions of a customer
        who does not use consolidated billing.
        """

        # The user does not use consolidated_billing => add each subscription to a separate document
        for subscription in self.get_subscriptions_prepared_for_billing(customer, billing_date,
                                                                        force_generate):
            provider = subscription.plan.provider

            document, discount_amounts = self._bill_subscription_into_document(subscription,
                                                                               billing_date)

            kwargs = {'entries_info': discount_amounts,
                      provider.flow: document}

            self._create_discount_entries(**kwargs)

            if provider.default_document_state == Provider.DEFAULT_DOC_STATE.ISSUED:
                document.issue()

    def _generate_for_single_subscription(self, subscription=None, billing_date=None,
                                          force_generate=False):
        """
        Generates the billing documents corresponding to a single subscription.
        Usually used when a subscription is ended with `when`=`now`.
        """

        billing_date = billing_date or timezone.now().date()

        provider = subscription.provider

        if not subscription.should_be_billed(billing_date) or force_generate:
            return

        document, discount_amounts = self._bill_subscription_into_document(subscription, billing_date)

        kwargs = {'entries_info': discount_amounts,
                  provider.flow: document}

        self._create_discount_entries(**kwargs)

        if provider.default_document_state == Provider.DEFAULT_DOC_STATE.ISSUED:
            document.issue()

    def add_subscription_cycles_to_document(
            self, billing_date, metered_features_billed_up_to, plan_billed_up_to, subscription,
            proforma=None, invoice=None
    ) -> Tuple[BillingLog, List[EntryInfo]]:
        entries_info: List[EntryInfo] = []

        plan_now_billed_up_to = plan_billed_up_to
        metered_features_now_billed_up_to = metered_features_billed_up_to

        plan_amount = Decimal('0.00')
        metered_features_amount = Decimal('0.00')

        # We iterate through each cycle (multiple bucket cycles can be contained within a billing
        # cycle) and add the entries to the document

        # relative_start_date and relative_end_date define the cycle that is billed within the
        # loop's iteration (referred throughout the comments as the cycle)
        still_billing_plan = subscription.should_plan_be_billed(billing_date)
        still_billing_mfs = subscription.should_mfs_be_billed(billing_date)

        while still_billing_mfs or still_billing_plan:
            # skip billing the plan during this loop if metered features have to catch up
            skip_billing_plan = (still_billing_mfs and plan_now_billed_up_to > metered_features_now_billed_up_to)

            if still_billing_plan and not skip_billing_plan:
                billed_up_to, entry_info = self._add_plan_cycle(
                    billing_date, plan_now_billed_up_to, subscription, proforma=proforma, invoice=invoice
                )

                if not billed_up_to:
                    still_billing_plan = False
                else:
                    plan_now_billed_up_to = billed_up_to
                    if entry_info:
                        plan_amount += entry_info.amount
                        entries_info.append(entry_info)

            skip_billing_mfs = still_billing_plan and metered_features_now_billed_up_to > plan_now_billed_up_to

            if still_billing_mfs and not skip_billing_mfs:
                billed_up_to, entry_info = self._add_mf_cycle(
                    billing_date, metered_features_now_billed_up_to, subscription, proforma=proforma, invoice=invoice
                )

                if not billed_up_to:
                    still_billing_mfs = False
                else:
                    metered_features_now_billed_up_to = billed_up_to
                    still_billing_mfs = subscription.should_mfs_be_billed(billing_date, billed_up_to=billed_up_to)
                    if entry_info:
                        metered_features_amount += entry_info.amount
                        entries_info.append(entry_info)

            if metered_features_now_billed_up_to == subscription.cancel_date:
                break

        billing_log = BillingLog.objects.create(
            subscription=subscription,
            invoice=invoice, proforma=proforma,
            total=plan_amount + metered_features_amount,
            plan_amount=plan_amount,
            metered_features_amount=metered_features_amount,
            billing_date=billing_date,
            metered_features_billed_up_to=metered_features_now_billed_up_to,
            plan_billed_up_to=plan_now_billed_up_to
        )

        return billing_log, entries_info

    def _add_plan_cycle(self, billing_date, plan_billed_up_to, subscription, proforma=None, invoice=None):
        relative_start_date = plan_billed_up_to + ONE_DAY
        relative_end_date = subscription.bucket_end_date(
            reference_date=relative_start_date, origin_type=OriginType.Plan
        )
        last_cycle_end_date = subscription.cycle_end_date(origin_type=OriginType.Plan,
                                                          reference_date=billing_date)

        if not (relative_start_date <= last_cycle_end_date):
            return None, None

        if not relative_end_date:
            # There was no cycle for the given billing date
            return None, None

        # This is here in order to separate the trial entries from the paid ones
        if (subscription.trial_end and
                relative_start_date <= subscription.trial_end <= relative_end_date):
            relative_end_date = subscription.trial_end

        # This cycle decision, based on cancel_date, should be moved into `cycle_start_date` and
        # `cycle_end_date`
        if subscription.cancel_date:
            relative_end_date = min(subscription.cancel_date, relative_end_date)

        # If the plan is prebilled we can only bill it if the cycle hasn't been billed before;
        # If the plan is not prebilled we can only bill it if the cycle has ended before the
        # billing date.
        should_bill_plan = (
            (plan_billed_up_to < relative_start_date) if subscription.prebill_plan else
            (relative_end_date < billing_date)
        )

        # Bill the plan amount
        if not should_bill_plan:
            return None, None

        if subscription.on_trial(relative_start_date):
            subscription._add_plan_trial(start_date=relative_start_date,
                                         end_date=relative_end_date,
                                         invoice=invoice, proforma=proforma)

            # Should return an entry info for trial as well, but need to filter it out from discounts
            entry_info = None
        else:
            amount, _ = subscription._add_plan_entries(start_date=relative_start_date,
                                                       end_date=relative_end_date,
                                                       proforma=proforma, invoice=invoice)

            entry_info = EntryInfo(
                start_date=relative_start_date,
                end_date=relative_end_date,
                origin_type=OriginType.Plan,
                subscription=subscription,
                amount=amount
            )

        return relative_end_date, entry_info

    def _add_mf_cycle(self, billing_date, metered_features_billed_up_to, subscription, proforma=None, invoice=None):
        relative_start_date = metered_features_billed_up_to + ONE_DAY

        relative_end_date = subscription.bucket_end_date(
            reference_date=relative_start_date,
            origin_type=OriginType.MeteredFeature,
        )
        last_cycle_end_date = subscription.cycle_end_date(origin_type=OriginType.MeteredFeature,
                                                          reference_date=billing_date)

        if not (relative_start_date <= last_cycle_end_date):
            return None, None

        if not relative_end_date:
            # There was no cycle for the given billing date
            return None, None

        # This is here in order to separate the trial entries from the paid ones
        if (subscription.trial_end and
                relative_start_date <= subscription.trial_end <= relative_end_date):
            relative_end_date = subscription.trial_end

        # This cycle decision, based on cancel_date, should be moved into `cycle_start_date` and
        # `cycle_end_date`
        if subscription.cancel_date:
            relative_end_date = min(subscription.cancel_date, relative_end_date)

        # Only bill metered features if the cycle the metered features belong to has ended
        # before the billing date.
        should_bill_metered_features = relative_end_date < billing_date

        # Bill the metered features
        if not should_bill_metered_features:
            return None, None

        if subscription.on_trial(relative_start_date):
            subscription._add_mfs_for_trial(
                start_date=relative_start_date, end_date=relative_end_date,
                invoice=invoice, proforma=proforma
            )

            # Should return an entry info for trial as well, but need to filter it out from discounts
            entry_info = None
        else:
            amount, _ = subscription._add_mfs_entries(
                start_date=relative_start_date, end_date=relative_end_date,
                proforma=proforma, invoice=invoice
            )

            entry_info = EntryInfo(
                start_date=relative_start_date,
                end_date=relative_end_date,
                origin_type=OriginType.MeteredFeature,
                subscription=subscription,
                amount=amount
            )

        return relative_end_date, entry_info

    def _create_document(self, subscription, billing_date) -> Union[Invoice, Proforma]:
        provider = subscription.provider
        customer = subscription.customer

        DocumentModel = (Proforma if provider.flow == provider.FLOWS.PROFORMA
                         else Invoice)

        document = DocumentModel.objects.create(provider=provider,
                                                customer=customer,
                                                currency=subscription.plan.currency)

        return document
