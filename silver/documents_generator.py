import datetime as dt
from decimal import Decimal

from django.utils import timezone
from dateutil.relativedelta import *

from silver.models import Customer, DocumentEntry


class DocumentsGenerator(object):
    def generate(self, subscription_id=None):
        """
        The `public` method called when one wants to generate the billing
        documents.
        """

        if not subscription_id:
            self._generate_all()
        else:
            self._generate_for_single_subscription(subscription_id)

    def _generate_for_single_subscription(self, subscription_id):
        """
        Generates the billing documents corresponding to a single subscription.
        Used when a subscription is ended with `when`=`now`
        """

        pass

    def _generate_all(self):
        """
        Generates the invoices/proformas for all the subscriptions that should
        be billed.
        """

        now = timezone.now().date()
        interval_start = dt.date(now.year, now.month, 1)

        for customer in Customer.objects.all():
            if customer.consolidated_billing:
                self._generate_for_user_with_consolidated_billing(customer,
                                                                  interval_start)
            else:
                self._generate_for_user_without_consolidated_billing(customer,
                                                                     interval_start)

    def _generate_for_user_with_consolidated_billing(self, customer, interval_start):
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
            if not subscription.should_be_billed(interval_start):
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
                                                 subscription, interval_start)
                cached_documents[provider] = document

            args = {
                'subscription': subscription,
                'interval_start': interval_start,
                provider.flow: document,
            }
            self._add_total_subscription_value_to_document(**args)

            if subscription.state == 'canceled':
                subscription.end()
                subscription.save()

        for provider, document in cached_documents.iteritems():
            if provider.default_document_state == 'issued':
                document.issue()
                document.save()

    def _generate_for_user_without_consolidated_billing(self, customer,
                                                        interval_start):
        """
        Generates the billing documents for all the subscriptions of a customer
        who does not use consolidated billing.
        """

        # The user does not use consolidated_billing => add each
        # subscription on a separate document (Invoice/Proforma)
        criteria = {'state__in': ['active', 'canceled']}
        for subscription in customer.subscriptions.filter(**criteria):
            if not subscription.should_be_billed(interval_start):
                continue

            provider = subscription.plan.provider
            document = self._create_document(provider, customer,
                                             subscription, interval_start)

            args = {
                'subscription': subscription,
                'interval_start': interval_start,
                provider.flow: document,
            }
            self._add_total_subscription_value_to_document(**args)

            if subscription.state == 'canceled':
                subscription.end()
                subscription.save()

            if provider.default_document_state == 'issued':
                document.issue()
                document.save()

    def _create_document(self, provider, customer, subscription, interval_start):
        """
        Creates and returns a BillingDocument object.
        """

        DocumentModel = provider.model_corresponding_to_default_flow

        payment_due_days = dt.timedelta(days=customer.payment_due_days)
        due_date = interval_start + payment_due_days
        document = DocumentModel.objects.create(provider=provider,
                                                customer=customer,
                                                due_date=due_date)

        return document

    def _add_total_subscription_value_to_document(self, subscription,
                                                  interval_start,
                                                  invoice=None, proforma=None):
        """
        Adds the total value of the subscription (value(plan) + value(consumed
        metered features)) to the document.
        """
        # TODO: what happens when a subscription is canceled, during any of
        # the intervals below.

        if subscription.is_billed_first_time:
            if subscription.was_on_trial(interval_start):
                self._add_plan_trial(subscription=subscription,
                                     start_date=subscription.start_date,
                                     end_date=interval_start, invoice=invoice,
                                     proforma=proforma)
                self._add_mfs_for_trial(subscription=subscription,
                                        start_date=subscription.start_date,
                                        end_date=interval_start, invoice=invoice,
                                        proforma=proforma)
                return
            else:
                # |start_date|---|trial_end|---|interval_end|
                # => 3 entries:
                # * The trial (+ and -)
                # * A prorated entry: (trial_end, now]
                self._add_plan_trial(subscription=subscription,
                                     start_date=subscription.start_date,
                                     end_date=subscription.trial_end,
                                     invoice=invoice, proforma=proforma)
                self._add_mfs_for_trial(subscription=subscription,
                                        start_date=subscription.start_date,
                                        end_date=subscription.trial_end,
                                        invoice=invoice, proforma=proforma)

                start_date = subscription.trial_end + dt.timedelta(days=1)
                self._add_plan_value(subscription=subscription,
                                     start_date=start_date,
                                     end_date=interval_start, invoice=invoice,
                                     proforma=proforma)
                self._add_mfs(subscription, start_date, interval_start,
                              invoice=invoice, proforma=proforma)
        else:
            last_billing_date = subscription.last_billing_date
            self._add_plan_value(subscription=subscription,
                                 start_date=last_billing_date,
                                 end_date=interval_start,
                                 invoice=invoice, proforma=proforma)
            self._add_mfs(subscription, last_billing_date, interval_start,
                          invoice=invoice, proforma=proforma)

    def _add_plan_trial(self, subscription, start_date, end_date, invoice=None,
                        proforma=None):
        """
        Adds the plan trial to the document, by adding an entry with positive
        prorated value and one with prorated, negative value which represents
        the discount for the trial period.
        """

        prorated, percent = self._get_proration_status_and_percent(
            subscription, start_date, end_date)
        plan_price = subscription.plan.amount * percent

        unit = '%ss' % subscription.plan.interval
        # TODO: add template
        template = "{plan_name} plan trial subscription ({start_date} - {end_date})"
        description = template.format(plan_name=subscription.plan.name,
                                      start_date=start_date,
                                      end_date=end_date)
        # Add plan with positive value
        DocumentEntry.objects.create(
            invoice=invoice, proforma=proforma, description=description,
            unit=unit, unit_price=plan_price, quantity=Decimal('1.00'),
            product_code=subscription.plan.product_code, prorated=prorated,
            start_date=start_date, end_date=end_date)

        # TODO: add template
        template = "{plan_name} plan trial discount ({start_date} - {end_date})"
        description = template.format(plan_name=subscription.plan.name,
                                      start_date=start_date,
                                      end_date=end_date)
        # Add plan with negative value
        DocumentEntry.objects.create(
            invoice=invoice, proforma=proforma, description=description,
            unit=unit, unit_price=-plan_price, quantity=Decimal('1.00'),
            product_code=subscription.plan.product_code, prorated=prorated,
            start_date=start_date, end_date=end_date)

    def _add_plan_value(self, subscription, start_date, end_date, invoice=None,
                        proforma=None):
        """
        Adds to the document the value of the plan.
        """

        prorated, percent = self._get_proration_status_and_percent(
            subscription, start_date, end_date)

        interval = '%sly' % subscription.plan.interval
        # TODO: add template
        if prorated:
            template = "{plan_name} Plan {interval} Prorated Subscription ({start_date} - {end_date})"
        else:
            template = "{plan_name} Plan {interval} Subscription ({start_date} - {end_date})"
        description = template.format(plan_name=subscription.plan.name,
                                      interval=interval,
                                      start_date=start_date,
                                      end_date=end_date)

        # Get the plan's prorated value
        plan_price = subscription.plan.amount * percent

        unit = '%ss' % subscription.plan.interval
        DocumentEntry.objects.create(
            invoice=invoice, proforma=proforma, description=description,
            unit=unit, unit_price=plan_price, quantity=Decimal('1.00'),
            product_code=subscription.plan.product_code, prorated=prorated,
            start_date=start_date, end_date=end_date
        )

    def _get_proration_status_and_percent(self, subscription, start_date, end_date):
        """
        Returns the proration percent (how much of the interval will be billed)
        and the status (if the subscription is prorated or not).

        :param date: the date at which the percent and status are calculated
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
        # NOTE (Important): this will be a NEGATIVE INTERVAL (e.g.: -1 month,
        # -1 week, etc.)
        interval_len = relativedelta(**intervals[subscription.plan.interval])

        if end_date + interval_len >= start_date:
            # |start_date|---|start_date+interval_len|---|end_date|
            # => not prorated
            return False, Decimal('1.0000')
        else:
            # |start_date|---|end_date|---|start_date+interval_len|
            # => prorated
            interval_start = end_date + interval_len
            days_in_interval = (end_date - interval_start).days
            days_since_subscription_start = (end_date - start_date).days
            percent = 1.0 * days_since_subscription_start / days_in_interval
            percent = Decimal(percent).quantize(Decimal('0.0000'))

            return True, percent

    def _get_included_units(self, subscription, metered_feature, start_date,
                            end_date):
        """
        Returns the number of items included in the subscription for a
        particulr metered feature. Useful to determine the number of mfs
        included in the subscription when a prorated entry is found.
        """

        pass

    def _get_consumed_units_during_trial(self, metered_feature, consumed_units):
        if metered_feature.included_units_during_trial:
            if consumed_units > metered_feature.included_units_during_trial:
                return consumed_units - metered_feature.included_units_during_trial
        return 0

    def _add_mfs_for_trial(self, subscription, start_date, end_date,
                           invoice=None, proforma=None):
        # Add all the metered features consumed during the trial period
        for metered_feature in subscription.plan.metered_features.all():
            qs = subscription.mf_log_entries.filter(metered_feature=metered_feature,
                                                    start_date__gte=start_date,
                                                    end_date__lte=end_date)
            log = [qs_item.consumed_units for qs_item in qs]
            total_consumed_units = reduce(lambda x, y: x + y, log, 0)

            extra_consumed_units = self._get_consumed_units_during_trial(
                metered_feature, total_consumed_units)

            if extra_consumed_units > 0:
                free_units = metered_feature.included_units_during_trial
                charged_units = extra_consumed_units
            else:
                free_units = total_consumed_units
                charged_units = 0

            if free_units > 0:
                template = "{name} ({start_date} - {end_date})."
                description = template.format(name=metered_feature.name,
                                              start_date=start_date,
                                              end_date=end_date)

                # Positive value for the consumed items. TODO: template
                DocumentEntry.objects.create(
                    invoice=invoice, proforma=proforma, description=description,
                    unit=metered_feature.unit, quantity=free_units,
                    unit_price=metered_feature.price_per_unit,
                    product_code=metered_feature.product_code,
                    start_date=start_date, end_date=end_date
                )

                # Negative value for the consumed items. TODO: template
                template = "{name} ({start_date} - {end_date}) trial discount."
                description = template.format(name=metered_feature.name,
                                              start_date=start_date,
                                              end_date=end_date)
                DocumentEntry.objects.create(
                    invoice=invoice, proforma=proforma, description=description,
                    unit=metered_feature.unit, quantity=free_units,
                    unit_price=-metered_feature.price_per_unit,
                    product_code=metered_feature.product_code,
                    start_date=start_date, end_date=end_date
                )

            # Extra items consumed items that are not included
            if charged_units > 0:
                # TODO: template
                template = "Extra {name} During Trial ({start_date} - {end_date})."
                description = template.format(name=metered_feature.name,
                                              start_date=start_date,
                                              end_date=end_date)
                DocumentEntry.objects.create(
                    invoice=invoice, proforma=proforma,
                    description=description, unit=metered_feature.unit,
                    quantity=charged_units,
                    unit_price=metered_feature.price_per_unit,
                    product_code=metered_feature.product_code,
                    start_date=start_date, end_date=end_date)

    def _get_consumed_units(self, subscription, metered_feature,
                            proration_percent, start_date, end_date):
        included_units = (proration_percent * metered_feature.included_units)

        qs = subscription.mf_log_entries.filter(metered_feature=metered_feature,
                                                start_date__gte=start_date,
                                                end_date__lte=end_date)
        log = [qs_item.consumed_units for qs_item in qs]
        total_consumed_units = reduce(lambda x, y: x + y, log, 0)

        if total_consumed_units > included_units:
            return total_consumed_units - included_units
        return 0

    def _add_mfs(self, subscription, start_date, end_date, invoice=None,
                 proforma=None):

        prorated, proration_percent = self._get_proration_status_and_percent(
            subscription, start_date, end_date)

        for metered_feature in subscription.plan.metered_features.all():
            consumed_units = self._get_consumed_units(subscription,
                                                      metered_feature,
                                                      proration_percent,
                                                      start_date, end_date)
            if consumed_units > 0:
                template = "Extra {name} ({start_date} - {end_date})."
                description = template.format(name=metered_feature.name,
                                            start_date=start_date,
                                            end_date=end_date)
                DocumentEntry.objects.create(
                    invoice=invoice, proforma=proforma,
                    description=description, unit=metered_feature.unit,
                    quantity=consumed_units, prorated=prorated,
                    unit_price=metered_feature.price_per_unit,
                    product_code=metered_feature.product_code,
                    start_date=start_date, end_date=end_date)
