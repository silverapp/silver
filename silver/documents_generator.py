import datetime
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

        for customer in Customer.objects.all():
            if customer.consolidated_billing:
                self._generate_for_user_with_consolidated_billing(customer,
                                                                  date=now)
            else:
                self._generate_for_user_without_consolidated_billing(customer,
                                                                     date=now)

    def _generate_for_user_with_consolidated_billing(self, customer, now):
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
            if not subscription.should_be_billed:
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
                                                 subscription, now)
                cached_documents[provider] = document

            self._add_subscription_to_document(subscription, provider, document,
                                               now)

            if subscription.state == 'canceled':
                subscription.end()
                subscription.save()

        for provider, document in cached_documents.iteritems():
            if provider.default_document_state == 'issued':
                document.issue()
                document.save()

    def _generate_for_user_without_consolidated_billing(self, customer, now):
        """
        Generates the billing documents for all the subscriptions of a customer
        who does not use consolidated billing.
        """

        # The user does not use consolidated_billing => add each
        # subscription on a separate document (Invoice/Proforma)
        criteria = {'state__in': ['active', 'canceled']}
        for subscription in customer.subscriptions.filter(**criteria):
            if not subscription.should_be_billed:
                continue

            provider = subscription.plan.provider
            document = self._create_document(provider, customer,
                                             subscription, now)

            self._add_subscription_to_document(subscription, document, now)

            if subscription.state == 'canceled':
                subscription.end()
                subscription.save()

            if provider.default_document_state == 'issued':
                document.issue()
                document.save()

    def _create_document(self, provider, customer, subscription, now_date):
        """
        Creates and returns a BillingDocument object.
        """

        DocumentModel = provider.model_corresponding_to_default_flow

        payment_due_days = datetime.timedelta(days=customer.payment_due_days)
        due_date = now_date + payment_due_days
        document = DocumentModel.objects.create(provider=provider,
                                                customer=customer,
                                                due_date=due_date)

        return document

    def _add_subscription_to_document(self, subscription, provider, document,
                                      now):
        """
        Adds the total value of the subscription (value(plan) + value(consumed
        metered features)) to the document.
        """

        args = {
            'subscription': subscription,
            'now': now,
            provider.flow: document,
        }
        self._add_plan_entry(**args)
        self._add_metered_features_entries(**args)

    def _add_plan_value(self, subscription, start_date, end_date, invoice=None,
                        proforma=None):
        """
        Adds to the document the value of the plan.
        """

        # Add plan value
        interval = '%sly' % subscription.plan.interval
        # TODO: add template
        template = "{plan_name} plan {interval} subscription ({start_date} - {end_date})"
        description = template.format(plan_name=subscription.plan.name,
                                      interval=interval,
                                      start_date=start_date,
                                      end_date=end_date)

        prorated, percent = self._get_proration_status_and_percent(
            subscription, start_date, end_date)

        # Get the plan's prorated value
        plan_price = subscription.plan.amount * percent

        unit = '%ss' % subscription.plan.interval
        DocumentEntry.objects.create(
            invoice=invoice, proforma=proforma, description=description,
            unit=unit, unit_price=plan_price, quantity=Decimal('1.00'),
            product_code=subscription.plan.product_code, prorated=prorated,
            start_date=start_date, end_date=end_date
        )

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

    def _add_mfs_for_trial(self, subscription, start_date, end_date,
                           invoice=None, proforma=None):

        # Add all the metered features between the trial period
        for metered_feature in subscription.plan.metered_features.all():
            log = subscription.mf_log_entries.filter(metered_feature=metered_feature,
                                                     start_date__gte=start_date,
                                                     end_date__lte=end_date)
            for log_item in log:
                # Positive value
                # TODO: add template
                template = "{name} ({start_date} - {end_date})."
                description = template.format(name=metered_feature.name,
                                              start_date=log_item.start_date,
                                              end_date=log_item.end_date)
                DocumentEntry.objects.create(
                    invoice=invoice, proforma=proforma, description=description,
                    unit=metered_feature.unit, quantity=log_item.consumed_item,
                    unit_price=metered_feature.price_per_unit,
                    product_code=metered_feature.product_code,
                    start_date=log_item.start_date, end_date=log_item.end_date)

                # Negative value
                # TODO: add template
                template = "{name} ({start_date} - {end_date}) trial discount."
                description = template.format(name=metered_feature.name,
                                              start_date=log_item.start_date,
                                              end_date=log_item.end_date)
                DocumentEntry.objects.create(
                    invoice=invoice, proforma=proforma, description=description,
                    unit=metered_feature.unit, quantity=log_item.consumed_item,
                    unit_price=-metered_feature.price_per_unit,
                    product_code=metered_feature.product_code,
                    start_date=log_item.start_date, end_date=log_item.end_date)

    def _add_mfs(self, subscription, start_date, end_date,
                 invoice=None, proforma=None):
        pass

    def _add_plan_entry(self, subscription, now, proforma=None, invoice=None):
        if subscription.is_billed_first_time:
            if subscription.is_on_trial:
                # First time billing and on trial => add only the trial entry
                # => add the trial and exit
                self._add_plan_trial(subscription=subscription,
                                     start_date=subscription.start_date,
                                     end_date=now, invoice=invoice,
                                     proforma=proforma)
                # TODO: add the mfs for this interval (positive + negative)
                return
            else:
                # First billing, but not on trial anymore
                intervals = {
                    'year': {'years': +subscription.plan.interval_count},
                    'month': {'months': +subscription.plan.interval_count},
                    'week': {'weeks': +subscription.plan.interval_count},
                    'day': {'days': +subscription.plan.interval_count},
                }
                interval_len = relativedelta(**intervals[subscription.plan.interval])

                if subscription.start_date + interval_len < now:
                    # |start_date|---|trial_end|---|start_date+interval_len|---|now|
                    # => 4 entries
                    # * The trial (+ and -)
                    # * A prorated entry: [trial_end, start_date + interval_len]
                    # * A prorated entry: [start_date + interval_len, now]
                    self._add_plan_trial(subscription=subscription,
                                         start_date=subscription.start_date,
                                         end_date=subscription.trial_end,
                                         invoice=invoice, proforma=proforma)
                    # TODO: add mfs for this interval (+ and -)

                    interval_end = subscription.start_date + interval_len
                    self._add_plan_value(subscription=subscription,
                                         start_date=subscription.trial_end,
                                         end_date=interval_end,
                                         invoice=invoice, proforma=proforma)
                    # TODO: add the mfs for this interval

                    self._add_plan_value(subscription=subscription,
                                         start_date=interval_end,
                                         end_date=now, invoice=invoice,
                                         proforma=proforma)
                    # TODO: add the mfs for this interval
                else:
                    # |start_date|---|trial_end|---|now|---|start_date+interval_len|
                    # => 3 entries:
                    # * The trial (+ and -)
                    # * A prorated entry: [trial_end, now]
                    self._add_plan_trial(subscription=subscription,
                                         start_date=subscription.start_date,
                                         end_date=subscription.trial_end,
                                         invoice=invoice, proforma=proforma)
                    # TODO: add mfs for this interval

                    self._add_plan_value(subscription=subscription,
                                         start_date=subscription.trial_end,
                                         end_date=now, invoice=invoice,
                                         proforma=proforma)
                    # TODO: add mfs for this interval
        else:
            # Was billed before => we use the last_billing_date to determine
            # the current end date
            last_billing_date = subscription.last_billing_date
            intervals = {
                'year': {'years': +subscription.plan.interval_count},
                'month': {'months': +subscription.plan.interval_count},
                'week': {'weeks': +subscription.plan.interval_count},
                'day': {'days': +subscription.plan.interval_count},
            }
            interval_len = relativedelta(**intervals[subscription.plan.interval])

            if subscription.state != 'canceled':
                if last_billing_date + interval_len < now_date:
                    # |last_billing_date|---|last_billing_date+interval_len|---|now|
                    # => 2 entries:
                    # * The full interval: [last_billing_date, last_billing_date+interval_len]
                    # * The prorated entry: [last_billing_date+interval_len, now]

                    interval_end = last_billing_date + interval_len
                    self._add_plan_value(subscription=subscription,
                                         start_date=last_billing_date,
                                         end_date=interval_end, invoice=invoice,
                                         proforma=proforma)
                    # TODO: add mfs for this interval

                    self._add_plan_value(subscription=subscription,
                                         start_date=interval_end,
                                         end_date=now, invoice=invoice,
                                         proforma=proforma)
                else:
                    # |last_billing_date|---|now|---|last_billing_date+interval_len|
                    # => 1 entry: the prorated plan
                    self._add_plan_value(subscription=subscription,
                                         start_date=last_billing_date,
                                         end_date=now, invoice=invoice,
                                         proforma=proforma)
                    # TODO: add mfs for this interval
            else:
                # TODO: Handle the case when the subscription was canceled
                pass

    def _add_metered_features_entries(self, subscription, date, proforma=None,
                                      invoice=None):
        pass
