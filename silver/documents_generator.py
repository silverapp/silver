import datetime as dt

from django.utils import timezone
from dateutil.relativedelta import *

from silver.models import Customer, Subscription, BillingDocument


class DocumentsGenerator(object):
    def generate(self, subscription=None, billing_date=None):
        """
        The `public` method called when one wants to generate the billing
        documents.

        .. warning:: For now, the generator works only for plans with single
        month intervals.
        """

        if not subscription:
            self._generate_all(billing_date=billing_date)
        else:
            self._generate_for_single_subscription(subscription=subscription,
                                                   billing_date=billing_date)

    def _generate_all(self, billing_date=None):
        """
        Generates the invoices/proformas for all the subscriptions that should
        be billed.
        """

        billing_date = billing_date or timezone.now().date()
        # billing_date -> the date when the billing documents are issued.

        for customer in Customer.objects.all():
            if customer.consolidated_billing:
                self._generate_for_user_with_consolidated_billing(customer,
                                                                  billing_date)
            else:
                self._generate_for_user_without_consolidated_billing(customer,
                                                                     billing_date)

    def _generate_for_user_with_consolidated_billing(self, customer,
                                                     billing_date):
        """
        Generates the billing documents for all the subscriptions of a customer
        who uses consolidated billing.
        """

        # For each provider there will be one invoice or proforma. The cache
        # is necessary as a certain customer might have more than one
        # subscription => all the subscriptions that belong to the same
        # provider will be added on the same invoice/proforma
        # => they are "cached".
        cached_documents = {}

        # Select all the active or canceled subscriptions
        criteria = {'state__in': ['active', 'canceled']}
        for subscription in customer.subscriptions.filter(**criteria):
            if not subscription.should_be_billed(billing_date):
                continue

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
            subscription.add_total_value_to_document(**args)

            if subscription.state == Subscription.STATES.canceled:
                subscription.end()
                subscription.save()

        for provider, document in cached_documents.iteritems():
            if provider.default_document_state == BillingDocument.STATES.issued:
                document.issue()
                document.save()

    def _generate_for_user_without_consolidated_billing(self, customer,
                                                        billing_date):
        """
        Generates the billing documents for all the subscriptions of a customer
        who does not use consolidated billing.
        """

        # The user does not use consolidated_billing => add each
        # subscription on a separate document (Invoice/Proforma)
        criteria = {'state__in': ['active', 'canceled']}
        for subscription in customer.subscriptions.filter(**criteria):
            if not subscription.should_be_billed(billing_date):
                continue

            provider = subscription.plan.provider
            document = self._create_document(provider, customer,
                                             subscription, billing_date)

            args = {
                'billing_date': billing_date,
                provider.flow: document,
            }
            subscription.add_total_value_to_document(**args)

            if subscription.state == Subscription.STATES.canceled:
                subscription.end()
                subscription.save()

            if provider.default_document_state == BillingDocument.STATES.issued:
                document.issue()
                document.save()

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
        subscription.add_total_value_to_document(**args)

        if subscription.state == Subscription.STATES.canceled:
            subscription.end()
            subscription.save()

        if provider.default_document_state == BillingDocument.STATES.issued:
            document.issue()
            document.save()

    def _create_document(self, provider, customer, subscription, billing_date):
        DocumentModel = provider.model_corresponding_to_default_flow

        payment_due_days = dt.timedelta(days=customer.payment_due_days)
        due_date = billing_date + payment_due_days
        document = DocumentModel.objects.create(provider=provider,
                                                customer=customer,
                                                due_date=due_date)

        return document
