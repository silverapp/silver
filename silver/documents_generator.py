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


import datetime as dt
import logging

from django.utils import timezone

from silver.models import Customer, Subscription, Proforma, Invoice, Provider

logger = logging.getLogger(__name__)


class DocumentsGenerator(object):
    def generate(self, subscription=None, billing_date=None, customers=None,
                 force_generate=False):
        """
        The `public` method called when one wants to generate the billing
        documents.

        .. warning:: For now, the generator works only for plans with single
        month intervals.

        .. note:: If `subscription` is passed, only the documents for that
            subscription are generated.
            If the `customers` parameter is passed, only the docments for those
            customers are generated.
            If neither the `subscription` nor the `customers` parameters are
            passed, the documents for all the customers are generated.

        :param subscription: the subscription for which one wants to generate the
            proformas/invoices.
        :param billing_date: the date used as billing date
        :param customers: the customers for which one wants to generate the
            proformas/invoices.
        :param force_generate: if True, invoices are generated at the date
            indicated by `billing_date` instead of the normal end of billing
            cycle.
        """

        if not subscription:
            customers = customers or Customer.objects.all()
            self._generate_all(billing_date=billing_date,
                               customers=customers,
                               force_generate=force_generate)
        else:
            self._generate_for_single_subscription(subscription=subscription,
                                                   billing_date=billing_date)

    def _generate_all(self, billing_date=None, customers=None,
                      force_generate=False):
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

    def _generate_for_user_with_consolidated_billing(self, customer,
                                                     billing_date,
                                                     force_generate):
        """
        Generates the billing documents for all the subscriptions of a customer
        who uses consolidated billing.
        """

        # Select all the active or canceled subscriptions
        subs_to_bill = []
        criteria = {'state__in': [Subscription.STATES.ACTIVE,
                                  Subscription.STATES.CANCELED]}
        for subscription in customer.subscriptions.filter(**criteria):
            if subscription.should_be_billed(billing_date):
                subs_to_bill.append(subscription)
                if (force_generate and subscription.state == Subscription.STATES.ACTIVE):
                    subscription.cancel(when=Subscription.CANCEL_OPTIONS.NOW)
                    subscription.save()
            elif force_generate and subscription.state == Subscription.STATES.CANCELED:
                subs_to_bill.append(subscription)
            elif force_generate and subscription.state == Subscription.STATES.ACTIVE:
                subscription.cancel(when=Subscription.CANCEL_OPTIONS.NOW)
                subscription.save()
                subs_to_bill.append(subscription)

        # For each provider there will be one invoice or proforma. The cache
        # is necessary as a certain customer might have more than one
        # subscription => all the subscriptions that belong to the same
        # provider will be added on the same invoice/proforma
        # => they are "cached".
        cached_documents = {}
        for subscription in subs_to_bill:
            provider = subscription.plan.provider
            if provider in cached_documents:
                # The BillingDocument was created beforehand, now just extract it
                # and add the new entries to the document.
                document = cached_documents[provider]
            else:
                # A BillingDocument instance does not exist for this provider
                # => create one
                document = self._create_document(provider, customer,
                                                 subscription, billing_date)
                cached_documents[provider] = document

            args = {
                'billing_date': billing_date,
                provider.flow: document,
            }

            self._log_subscription_billing(document, subscription)

            subscription.add_total_value_to_document(**args)

            if subscription.state == Subscription.STATES.CANCELED:
                subscription.end()
                subscription.save()

        for provider, document in cached_documents.iteritems():
            if provider.default_document_state == Provider.DEFAULT_DOC_STATE.ISSUED:
                document.issue()

    def _generate_for_user_without_consolidated_billing(self, customer,
                                                        billing_date,
                                                        force_generate):
        """
        Generates the billing documents for all the subscriptions of a customer
        who does not use consolidated billing.
        """

        # The user does not use consolidated_billing => add each
        # subscription on a separate document (Invoice/Proforma)
        subs_to_bill = []
        criteria = {'state__in': [Subscription.STATES.ACTIVE,
                                  Subscription.STATES.CANCELED]}
        for subscription in customer.subscriptions.filter(**criteria):
            if subscription.should_be_billed(billing_date):
                subs_to_bill.append(subscription)
                if (force_generate and subscription.state == Subscription.STATES.ACTIVE):
                    subscription.cancel(when=Subscription.CANCEL_OPTIONS.NOW)
                    subscription.save()
            elif force_generate and subscription.state == Subscription.STATES.CANCELED:
                subs_to_bill.append(subscription)
            elif force_generate and subscription.state == Subscription.STATES.ACTIVE:
                subscription.cancel(when=Subscription.CANCEL_OPTIONS.NOW)
                subscription.save()
                subs_to_bill.append(subscription)

        for subscription in subs_to_bill:
            provider = subscription.plan.provider
            document = self._create_document(provider, customer,
                                             subscription, billing_date)

            args = {
                'billing_date': billing_date,
                provider.flow: document,
            }

            self._log_subscription_billing(document, subscription)

            subscription.add_total_value_to_document(**args)

            if subscription.state == Subscription.STATES.CANCELED:
                subscription.end()
                subscription.save()

            if provider.default_document_state == Provider.DEFAULT_DOC_STATE.ISSUED:
                document.issue()

    def _generate_for_single_subscription(self, subscription=None,
                                          billing_date=None):
        """
        Generates the billing documents corresponding to a single subscription.
        Used when a subscription is ended with `when`=`now`
        """

        billing_date = billing_date or timezone.now().date()

        provider = subscription.plan.provider
        customer = subscription.customer

        document = self._create_document(provider, customer, subscription,
                                         billing_date)
        args = {
            'billing_date': billing_date,
            provider.flow: document,
        }

        self._log_subscription_billing(document, subscription)

        subscription.add_total_value_to_document(**args)

        if subscription.state == Subscription.STATES.CANCELED:
            subscription.end()
            subscription.save()

        if provider.default_document_state == Provider.DEFAULT_DOC_STATE.ISSUED:
            document.issue()

    def _create_document(self, provider, customer, subscription, billing_date):
        DocumentModel = (Proforma if provider.flow == provider.FLOWS.PROFORMA
                         else Invoice)

        payment_due_days = dt.timedelta(days=customer.payment_due_days)
        due_date = billing_date + payment_due_days
        document = DocumentModel.objects.create(provider=provider,
                                                customer=customer,
                                                due_date=due_date)

        return document
