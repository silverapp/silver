# -*- coding: utf-8 -*-
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


import datetime
from decimal import Decimal

import factory
import factory.fuzzy

from django.contrib.auth import get_user_model
from django.utils import timezone

from silver.models import (Provider, Plan, MeteredFeature, Customer,
                           Subscription, Invoice, ProductCode,
                           Proforma, MeteredFeatureUnitsLog, DocumentEntry,
                           Transaction, PaymentMethod)
from silver.utils.international import countries
from silver.tests.fixtures import manual_processor


class ProductCodeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProductCode

    value = factory.Sequence(lambda n: 'ProductCode{cnt}'.format(cnt=n))


class CustomerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Customer

    first_name = factory.Sequence(lambda n: u'FirstNáme{cnt}'.format(cnt=n))
    last_name = factory.Sequence(lambda n: u'LastNáme{cnt}'.format(cnt=n))
    company = factory.Sequence(lambda n: u'Compány{cnt}'.format(cnt=n))
    email = factory.Sequence(lambda n: u'some{cnt}@email.com'.format(cnt=n))
    address_1 = factory.Sequence(lambda n: u'Addrâss1{cnt}'.format(cnt=n))
    address_2 = factory.Sequence(lambda n: u'Addrãess2{cnt}'.format(cnt=n))
    country = factory.Sequence(lambda n: countries[n % len(countries)][0])
    city = factory.Sequence(lambda n: u'Citŷ{cnt}'.format(cnt=n))
    state = factory.Sequence(lambda n: 'State{cnt}'.format(cnt=n))
    zip_code = factory.Sequence(lambda n: str(n))
    phone = factory.Sequence(str)
    extra = factory.Sequence(lambda n: 'Extra{cnt}'.format(cnt=n))
    meta = factory.Sequence(lambda n: {"something": [n, n + 1]})
    consolidated_billing = True

    customer_reference = factory.Sequence(lambda n: 'Reference{cnt}'.format(cnt=n))
    sales_tax_percent = Decimal(1.0)
    sales_tax_name = factory.Sequence(lambda n: 'VAT'.format(cnt=n))
    payment_due_days = 5


class MeteredFeatureFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MeteredFeature

    name = factory.Sequence(lambda n: u'Náme{cnt}'.format(cnt=n))
    unit = factory.Sequence(lambda n: 'MeteredFeature{cnt}Unit'.format(cnt=n))
    price_per_unit = factory.fuzzy.FuzzyDecimal(low=0.01, high=100.00,
                                                precision=4)
    included_units = factory.fuzzy.FuzzyDecimal(low=0.01, high=100000.00,
                                                precision=4)
    product_code = factory.SubFactory(ProductCodeFactory)


class ProviderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Provider

    name = factory.Sequence(lambda n: u'Náme{cnt}'.format(cnt=n))
    company = factory.Sequence(lambda n: u'Compány{cnt}'.format(cnt=n))
    email = factory.Sequence(
        lambda n: u'provider{cnt}@email.com'.format(cnt=n)
    )
    address_1 = factory.Sequence(lambda n: u'Addãress1{cnt}'.format(cnt=n))
    address_2 = factory.Sequence(lambda n: u'Addåress2{cnt}'.format(cnt=n))
    country = factory.Sequence(lambda n: countries[n % len(countries)][0])
    city = factory.Sequence(lambda n: u'Citŷ{cnt}'.format(cnt=n))
    state = factory.Sequence(lambda n: 'State{cnt}'.format(cnt=n))
    zip_code = factory.Sequence(lambda n: str(n))
    extra = factory.Sequence(lambda n: 'Extra{cnt}'.format(cnt=n))
    meta = factory.Sequence(lambda n: {"something": [n, n + 1]})

    flow = 'proforma'
    invoice_series = 'InvoiceSeries'
    invoice_starting_number = 1
    proforma_series = 'ProformaSeries'
    proforma_starting_number = 1


class PlanFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Plan

    name = factory.Sequence(lambda n: u'Náme{cnt}'.format(cnt=n))
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
        lambda obj: obj.start_date + datetime.timedelta(days=obj.plan.trial_period_days)
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

    number = factory.Sequence(lambda n: n)
    customer = factory.SubFactory(CustomerFactory)
    provider = factory.SubFactory(ProviderFactory)
    currency = 'RON'
    transaction_currency = 'RON'
    transaction_xe_rate = Decimal(1)
    state = Invoice.STATES.DRAFT
    issue_date = factory.LazyAttribute(
        lambda invoice: timezone.now().date() if invoice.state == Invoice.STATES.ISSUED else None
    )

    @factory.post_generation
    def invoice_entries(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            # A list of groups were passed in, use them
            for invoice_entry in extracted:
                self.invoice_entries.add(invoice_entry)


class ProformaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Proforma

    number = factory.Sequence(lambda n: n)
    customer = factory.SubFactory(CustomerFactory)
    provider = factory.SubFactory(ProviderFactory)
    currency = 'RON'
    transaction_currency = 'RON'
    transaction_xe_rate = Decimal(1)
    state = Proforma.STATES.DRAFT
    issue_date = factory.LazyAttribute(
        lambda proforma: timezone.now().date() if proforma.state == Proforma.STATES.ISSUED else None
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


class DocumentEntryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DocumentEntry

    description = factory.Sequence(lambda n: 'Description{cnt}'.format(cnt=n))
    unit = factory.Sequence(lambda n: 'Unit{cnt}'.format(cnt=n))
    quantity = factory.fuzzy.FuzzyDecimal(low=0.00, high=50000.00, precision=4)
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
            proforma.invoice = invoice
            if invoice:
                proforma.transaction_currency = invoice.transaction_currency
            proforma.save()

        if invoice:
            invoice.proforma = proforma
            if proforma:
                invoice.transaction_currency = proforma.transaction_currency
            invoice.save()

        return super(TransactionFactory, cls)._create(model_class, *args, **kwargs)
