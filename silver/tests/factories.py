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

import datetime
import factory
import factory.fuzzy

from decimal import Decimal
from faker import Faker

from django.contrib.auth import get_user_model
from django.utils import timezone

from silver.models import (Provider, Plan, MeteredFeature, Customer,
                           Subscription, Invoice, ProductCode, PDF,
                           Proforma, MeteredFeatureUnitsLog, DocumentEntry,
                           Transaction, PaymentMethod, BillingLog)
from silver.tests.fixtures import manual_processor
from silver.utils.dates import last_day_of_month, prev_month

faker = Faker(locale='hu_HU')


class ProductCodeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProductCode

    value = factory.Sequence(lambda n: faker.ean8())


class CustomerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Customer

    first_name = factory.Sequence(lambda n: faker.first_name())
    last_name = factory.Sequence(lambda n: faker.last_name())
    company = factory.Sequence(lambda n: faker.company())
    email = factory.Sequence(lambda n: faker.company_email())
    address_1 = factory.Sequence(lambda n: faker.address())
    address_2 = factory.Sequence(lambda n: faker.address())
    country = factory.Sequence(lambda n: faker.country_code())
    city = factory.Sequence(lambda n: faker.city())
    state = factory.Sequence(lambda n: faker.city_part())
    zip_code = factory.Sequence(lambda n: faker.postcode())
    phone = factory.Sequence(lambda n: faker.phone_number())
    extra = factory.Sequence(lambda n: faker.text())
    meta = factory.Sequence(lambda n: {"something": [n, n + 1]})
    consolidated_billing = True

    customer_reference = factory.Sequence(lambda n: faker.uuid4())
    sales_tax_percent = Decimal(1.0)
    sales_tax_name = factory.Sequence(lambda n: 'VAT')
    payment_due_days = 5


class MeteredFeatureFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MeteredFeature

    name = factory.Sequence(lambda n: faker.sentence(nb_words=2))
    unit = factory.Sequence(lambda n: 'MeteredFeature{cnt}Unit'.format(cnt=n))
    price_per_unit = factory.fuzzy.FuzzyDecimal(low=0.01, high=100.00,
                                                precision=4)
    included_units = factory.fuzzy.FuzzyDecimal(low=0.01, high=100000.00,
                                                precision=4)
    product_code = factory.SubFactory(ProductCodeFactory)


class ProviderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Provider

    name = factory.Sequence(lambda n: faker.name())
    company = factory.Sequence(lambda n: faker.company())
    email = factory.Sequence(lambda n: faker.company_email())
    address_1 = factory.Sequence(lambda n: faker.address())
    address_2 = factory.Sequence(lambda n: faker.address())
    country = factory.Sequence(lambda n: faker.country_code())
    city = factory.Sequence(lambda n: faker.city())
    state = factory.Sequence(lambda n: faker.city_part())
    zip_code = factory.Sequence(lambda n: faker.postcode())
    extra = factory.Sequence(lambda n: faker.text())
    meta = factory.Sequence(lambda n: {"something": [n, n + 1]})

    flow = 'proforma'
    invoice_series = 'InvoiceSeries'
    invoice_starting_number = 1
    proforma_series = 'ProformaSeries'
    proforma_starting_number = 1


class PlanFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Plan

    name = factory.Sequence(lambda n: faker.name())
    interval = Plan.INTERVALS.MONTH
    interval_count = factory.Sequence(lambda n: n)
    amount = factory.Sequence(lambda n: n)
    currency = 'USD'
    generate_after = factory.Sequence(lambda n: n)
    enabled = factory.Sequence(lambda n: n % 2 != 0)
    private = factory.Sequence(lambda n: n % 2 != 0)
    product_code = factory.SubFactory(ProductCodeFactory)
    provider = factory.SubFactory(ProviderFactory)

    @factory.post_generation
    def metered_features(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            # A list of groups were passed in, use them
            for metered_feature in extracted:
                self.metered_features.add(metered_feature)


class SubscriptionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Subscription

    plan = factory.SubFactory(PlanFactory)
    customer = factory.SubFactory(CustomerFactory)
    start_date = timezone.now().date()
    trial_end = factory.LazyAttribute(
        lambda obj: obj.start_date + datetime.timedelta(days=obj.plan.trial_period_days - 1)
        if obj.plan.trial_period_days else None)
    reference = factory.Sequence(lambda n: "{}".format(n))
    meta = factory.Sequence(lambda n: {"something": [n, n + 1]})

    @factory.post_generation
    def metered_features(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            # A list of groups were passed in, use them
            for metered_feature in extracted:
                self.metered_features.add(metered_feature)


class MeteredFeatureUnitsLogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MeteredFeatureUnitsLog
    metered_feature = factory.SubFactory(MeteredFeatureFactory)
    subscription = factory.SubFactory(SubscriptionFactory)
    consumed_units = factory.fuzzy.FuzzyDecimal(low=0.01, high=50000.00,
                                                precision=4)


class InvoiceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Invoice

    customer = factory.SubFactory(CustomerFactory)
    provider = factory.SubFactory(ProviderFactory)
    currency = 'RON'
    transaction_currency = 'RON'
    transaction_xe_rate = Decimal(1)
    state = Invoice.STATES.DRAFT
    issue_date = factory.LazyAttribute(
        lambda invoice: (faker.past_datetime(start_date="-200d", tzinfo=None)
                         if invoice.state != Invoice.STATES.DRAFT else None)
    )
    paid_date = factory.LazyAttribute(
        lambda invoice: timezone.now().date() if invoice.state == Invoice.STATES.PAID else None
    )
    cancel_date = factory.LazyAttribute(
        lambda invoice: timezone.now().date() if invoice.state == Invoice.STATES.CANCELED else None
    )

    @factory.post_generation
    def invoice_entries(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            # A list of groups were passed in, use them
            for invoice_entry in extracted:
                self.invoice_entries.add(invoice_entry)

        if self.state != 'draft':
            self._total = self.compute_total()
            self._total_in_transaction_currency = self.compute_total_in_transaction_currency()
            self.save()


class ProformaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Proforma

    customer = factory.SubFactory(CustomerFactory)
    provider = factory.SubFactory(ProviderFactory)
    currency = 'RON'
    transaction_currency = 'RON'
    transaction_xe_rate = Decimal(1)
    state = Proforma.STATES.DRAFT
    issue_date = factory.LazyAttribute(
        lambda proforma: (faker.past_datetime(start_date="-200d", tzinfo=None)
                          if proforma.state != Invoice.STATES.DRAFT else None)
    )
    paid_date = factory.LazyAttribute(
        lambda proforma: timezone.now().date() if proforma.state == Invoice.STATES.PAID else None
    )
    cancel_date = factory.LazyAttribute(
        lambda proforma: (timezone.now().date()
                          if proforma.state == Invoice.STATES.CANCELED else None)
    )

    @factory.post_generation
    def subscriptions(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for subscription in extracted:
                self.subscriptions.add(subscription)

    @factory.post_generation
    def proforma_entries(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            # A list of groups were passed in, use them
            for proforma_entry in extracted:
                self.proforma_entries.add(proforma_entry)

        if self.state != Proforma.STATES.DRAFT:
            self._total = self.compute_total()
            self._total_in_transaction_currency = self.compute_total_in_transaction_currency()
            self.save()


class DocumentEntryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DocumentEntry

    description = factory.Sequence(lambda n: 'Description{cnt}'.format(cnt=n))
    unit = factory.Sequence(lambda n: 'Unit{cnt}'.format(cnt=n))
    quantity = factory.fuzzy.FuzzyDecimal(low=1.00, high=50000.00, precision=4)
    unit_price = factory.fuzzy.FuzzyDecimal(low=0.01, high=100.00, precision=4)
    product_code = factory.SubFactory(ProductCodeFactory)
    end_date = factory.Sequence(
        lambda n: datetime.date.today() + datetime.timedelta(days=n))
    start_date = datetime.date.today()
    prorated = factory.Sequence(lambda n: n % 2 == 1)


class AdminUserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_user_model()

    username = 'admin'
    email = 'admin@admin.com'
    password = factory.PostGenerationMethodCall('set_password', 'admin')
    is_active = True
    is_superuser = True
    is_staff = True


class PaymentMethodFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PaymentMethod

    payment_processor = manual_processor
    customer = factory.SubFactory(CustomerFactory)


class TransactionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Transaction

    payment_method = factory.SubFactory(PaymentMethodFactory)
    proforma = factory.SubFactory(
        ProformaFactory,
        customer=factory.SelfAttribute('..payment_method.customer'),
        state=Proforma.STATES.ISSUED,
        issue_date=timezone.now().date(),
        transaction_xe_rate=Decimal('1')
    )
    invoice = factory.SubFactory(
        InvoiceFactory,
        customer=factory.SelfAttribute('..payment_method.customer'),
        state=Invoice.STATES.ISSUED,
        issue_date=timezone.now().date(),
        transaction_xe_rate=Decimal('1')
    )

    state = Transaction.States.Initial

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        invoice = kwargs.get('invoice')
        proforma = kwargs.get('proforma')
        if proforma:
            proforma.related_document = invoice
            if invoice:
                proforma.transaction_currency = invoice.transaction_currency
            proforma.save()

        if invoice:
            invoice.related_document = proforma
            if proforma:
                invoice.transaction_currency = proforma.transaction_currency
            invoice.save()

        return super(TransactionFactory, cls)._create(model_class, *args, **kwargs)


class PDFFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PDF


class BillingLogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BillingLog

    subscription = factory.SubFactory(SubscriptionFactory)

    proforma = factory.SubFactory(
        ProformaFactory,
        customer=factory.SelfAttribute('..subscription.customer'),
        state=Invoice.STATES.ISSUED,
        issue_date=timezone.now().date(),
    )
    invoice = factory.SubFactory(
        InvoiceFactory,
        customer=factory.SelfAttribute('..subscription.customer'),
        state=Invoice.STATES.ISSUED,
        issue_date=timezone.now().date(),
    )
    billing_date = timezone.now().date()
    plan_billed_up_to = last_day_of_month(timezone.now().date())
    metered_features_billed_up_to = last_day_of_month(prev_month(timezone.now().date()))
