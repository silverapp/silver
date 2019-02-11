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
from itertools import chain

import logging

from decimal import Decimal
from django.db import transaction

from django.utils import timezone

from silver.models import Customer, Subscription, Proforma, Invoice, Provider, BillingLog
from silver.utils.dates import ONE_DAY


logger = logging.getLogger(__name__)


class DocumentsGenerator(object):
    def generate(self, subscription=None, billing_date=None, customers=None, force_generate=False):
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
        :returns: A list of generated documents.

        :note
                If `subscription` is passed, only the documents for that subscription are
            generated.
                If the `customers` parameter is passed, only the documents for those customers are
            generated.
                Only one of the `customers` and `subscription` parameters may be passed at a time.
                If neither the `subscription` nor the `customers` parameters are passed, the
                documents for all the customers will be generated.
        """

        if not subscription:
            customers = customers or Customer.objects.all()
            return self._generate_all(billing_date=billing_date,
                                      customers=customers,
                                      force_generate=force_generate)
        else:
            return self._generate_for_single_subscription(subscription=subscription,
                                                          billing_date=billing_date,
                                                          force_generate=force_generate)

    def _generate_all(self, billing_date=None, customers=None, force_generate=False):
        """
        Generates the invoices/proformas for all the subscriptions that should
        be billed.
        """

        billing_date = billing_date or timezone.now().date()
        # billing_date -> the date when the billing documents are issued.

        documents = []
        for customer in customers:
            if customer.consolidated_billing:
                documents += self._generate_for_user_with_consolidated_billing(
                    customer, billing_date, force_generate
                )
            else:
                documents += self._generate_for_user_without_consolidated_billing(
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

    def _bill_subscription_into_document(self, subscription, billing_date, document=None):
        if not document:
            document = self._create_document(subscription, billing_date)

        self._log_subscription_billing(document, subscription)

        kwargs = subscription.billed_up_to_dates

        kwargs.update({
            'billing_date': billing_date,
            'subscription': subscription,
            subscription.provider.flow: document,
        })
        with transaction.atomic():
            self.add_subscription_cycles_to_document(**kwargs)

            if subscription.state == Subscription.STATES.CANCELED:
                subscription.end()
                subscription.save()

            if subscription.provider.default_document_state == Provider.DEFAULT_DOC_STATE.ISSUED:
                document.issue()

        return document

    def _generate_for_user_with_consolidated_billing(self, customer, billing_date, force_generate):
        """
        Generates the billing documents for all the subscriptions of a customer
        who uses consolidated billing.
        """

        # For each provider there will be one invoice or proforma. The cache is necessary as a
        # certain customer might have more than one subscription
        # => all the subscriptions belonging to the same provider will be added to the same document

        existing_provider_documents = {}
        for subscription in self.get_subscriptions_prepared_for_billing(customer, billing_date,
                                                                        force_generate):
            provider = subscription.plan.provider

            existing_document = existing_provider_documents.get(provider)

            existing_provider_documents[provider] = self._bill_subscription_into_document(
                subscription, billing_date, document=existing_document
            )

        return list(chain(existing_provider_documents.items()))

    def _generate_for_user_without_consolidated_billing(self, customer, billing_date,
                                                        force_generate):
        """
        Generates the billing documents for all the subscriptions of a customer
        who does not use consolidated billing.
        """

        # The user does not use consolidated_billing => add each subscription to a separate document
        subscriptions_to_bill = self.get_subscriptions_prepared_for_billing(customer, billing_date,
                                                                            force_generate)
        return [self._bill_subscription_into_document(subscription, billing_date)
                for subscription in subscriptions_to_bill]

    def _generate_for_single_subscription(self, subscription=None, billing_date=None,
                                          force_generate=False):
        """
        Generates the billing documents corresponding to a single subscription.
        Usually used when a subscription is ended with `when`=`now`.
        """

        billing_date = billing_date or timezone.now().date()

        if not subscription.should_be_billed(billing_date) or force_generate:
            return []

        return [self._bill_subscription_into_document(subscription, billing_date)]

    def add_subscription_cycles_to_document(self, billing_date, metered_features_billed_up_to,
                                            plan_billed_up_to, subscription,
                                            proforma=None, invoice=None):
        relative_start_date = metered_features_billed_up_to + ONE_DAY
        plan_now_billed_up_to = plan_billed_up_to
        metered_features_now_billed_up_to = metered_features_billed_up_to

        prebill_plan = subscription.prebill_plan

        plan_amount = Decimal('0.00')
        metered_features_amount = Decimal('0.00')

        last_cycle_end_date = subscription.cycle_end_date(billing_date)

        # We iterate through each cycle (multiple bucket cycles can be contained within a billing
        # cycle) and add the entries to the document

        # relative_start_date and relative_end_date define the cycle that is billed within the
        # loop's iteration (referred throughout the comments as a cycle)
        while relative_start_date <= last_cycle_end_date:
            relative_end_date = subscription.bucket_end_date(reference_date=relative_start_date)

            # There was no cycle for the given billing date
            if not relative_end_date:
                break

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
            should_bill_plan = ((plan_billed_up_to < relative_start_date) if prebill_plan else
                                (relative_end_date < billing_date))

            # Bill the plan amount
            if should_bill_plan:
                plan_amount += self.add_plan_entry(
                    subscription, start_date=relative_start_date, end_date=relative_end_date,
                    invoice=invoice, proforma=proforma
                )
                plan_now_billed_up_to = relative_end_date

            # Only bill metered features if the cycle the metered features belong to has ended
            # before the billing date.
            should_bill_metered_features = relative_end_date < billing_date

            # Bill the metered features
            if should_bill_metered_features:
                metered_features_amount += self.add_plan_metered_features(
                    subscription, start_date=relative_start_date, end_date=relative_end_date,
                    invoice=invoice, proforma=proforma
                )
                metered_features_now_billed_up_to = relative_end_date

            # Obtain a start date for the next iteration (cycle)
            relative_start_date = relative_end_date + ONE_DAY

            if relative_end_date == subscription.cancel_date:
                break

        BillingLog.objects.create(subscription=subscription,
                                  invoice=invoice, proforma=proforma,
                                  total=plan_amount + metered_features_amount,
                                  plan_amount=plan_amount,
                                  metered_features_amount=metered_features_amount,
                                  billing_date=billing_date,
                                  metered_features_billed_up_to=metered_features_now_billed_up_to,
                                  plan_billed_up_to=plan_now_billed_up_to)

    def _create_document(self, subscription, billing_date):
        provider = subscription.provider
        customer = subscription.customer

        DocumentModel = (Proforma if provider.flow == provider.FLOWS.PROFORMA
                         else Invoice)

        payment_due_days = dt.timedelta(days=customer.payment_due_days)
        due_date = billing_date + payment_due_days
        document = DocumentModel.objects.create(provider=provider,
                                                customer=customer,
                                                due_date=due_date,
                                                currency=subscription.plan.currency)

        return document

    def add_plan_entry(self, subscription, start_date, end_date, invoice=None, proforma=None):
        if subscription.on_trial(start_date):
            return subscription._add_plan_trial(start_date=start_date,  end_date=end_date,
                                                invoice=invoice, proforma=proforma)
        else:
            return subscription._add_plan_value(start_date=start_date, end_date=end_date,
                                                proforma=proforma, invoice=invoice)

    def add_plan_metered_features(self, subscription, start_date, end_date,
                                  invoice=None, proforma=None):
        if subscription.on_trial(start_date):
            return subscription._add_mfs_for_trial(start_date=start_date, end_date=end_date,
                                                   invoice=invoice, proforma=proforma)
        else:
            return subscription._add_mfs(start_date=start_date, end_date=end_date,
                                         proforma=proforma, invoice=invoice)
