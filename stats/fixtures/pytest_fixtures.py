import pytest
from datetime import datetime, timedelta

import pytz
from decimal import Decimal
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from silver.models import Invoice, Transaction, Subscription, BillingLog
from silver.tests.factories import TransactionFactory, InvoiceFactory, DocumentEntryFactory, \
    SubscriptionFactory, PlanFactory, ProviderFactory, CustomerFactory

UserModel = get_user_model()


@pytest.fixture()
def user():
    return UserModel.objects.create_superuser(
        username='test', email='test@...', password='top_secret')


@pytest.fixture()
def api_client(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.fixture()
def customers():
    customers_list = []
    customers_list.append(CustomerFactory.create(first_name='Harry', last_name='Potter'))
    customers_list.append(CustomerFactory.create(first_name='Ron', last_name='Weasley'))
    customers_list.append(CustomerFactory.create(first_name='Hermione', last_name='Granger'))
    return customers_list


@pytest.fixture()
def document_entries():
    entries_list = []
    entries_list.append(DocumentEntryFactory(quantity=2, unit_price=100))
    entries_list.append(DocumentEntryFactory(quantity=1, unit_price=100))
    entries_list.append(DocumentEntryFactory(quantity=3, unit_price=100))
    return entries_list


@pytest.fixture()
def plans():
    plans_list = []
    provider = ProviderFactory.create(name='Presslabs')
    plans_list.append(PlanFactory.create(name='Oxygen', amount=150, currency='RON',
                                         provider=provider, generate_after=120))
    plans_list.append(PlanFactory.create(name='Hydrogen', amount=499, currency='USD',
                                         provider=provider, generate_after=120))
    plans_list.append(PlanFactory.create(name='Enterprise', amount=1999, currency='USD',
                                         provider=provider, generate_after=120))
    return plans_list


@pytest.fixture()
def subscriptions(customers, plans):
    test_date = datetime(2017, 1, 11, 10, 56, 24, 898509, pytz.UTC)
    test_amount = 10

    subscription = SubscriptionFactory.create(plan=plans[0], state=Subscription.STATES.ACTIVE,
                                              customer=customers[0])
    BillingLog.objects.create(subscription=subscription, billing_date=test_date, total=test_amount,
                              plan_billed_up_to=test_date, metered_features_billed_up_to=test_date)
    test_amount += 10
    test_date += timedelta(20)

    subscription = SubscriptionFactory.create(plan=plans[1], state=Subscription.STATES.ACTIVE,
                                              customer=customers[0])
    BillingLog.objects.create(subscription=subscription, billing_date=test_date, total=test_amount,
                              plan_billed_up_to=test_date, metered_features_billed_up_to=test_date)

    subscription = SubscriptionFactory.create(plan=plans[0], state=Subscription.STATES.ACTIVE,
                                              customer=customers[1])
    BillingLog.objects.create(subscription=subscription, billing_date=test_date, total=test_amount,
                              plan_billed_up_to=test_date, metered_features_billed_up_to=test_date)
    BillingLog.objects.create(subscription=subscription, billing_date=test_date, total=test_amount,
                              plan_billed_up_to=test_date, metered_features_billed_up_to=test_date)

    test_amount += 10
    test_date += timedelta(20)

    subscription = SubscriptionFactory.create(plan=plans[2], state=Subscription.STATES.ACTIVE,
                                              customer=customers[1])
    BillingLog.objects.create(subscription=subscription, billing_date=test_date, total=test_amount,
                              plan_billed_up_to=test_date, metered_features_billed_up_to=test_date)


@pytest.fixture()
def documents(customers, document_entries):

    test_date = datetime(2017, 9, 11, 10, 56, 24, 898509, pytz.UTC)
    test_date = test_date + timedelta(-15)
    InvoiceFactory.create(invoice_entries=[document_entries[1]], state=Invoice.STATES.ISSUED,
                          proforma=None, issue_date=test_date, customer=customers[0])

    test_date = test_date + timedelta(-15)
    InvoiceFactory.create(invoice_entries=[document_entries[0]], state=Invoice.STATES.ISSUED,
                          proforma=None, issue_date=test_date, customer=customers[1])
    InvoiceFactory.create(invoice_entries=[document_entries[0]], state=Invoice.STATES.ISSUED,
                          proforma=None, issue_date=test_date + timedelta(-4),
                          customer=customers[1])

    test_date = test_date + timedelta(-15)
    InvoiceFactory.create(invoice_entries=[document_entries[2]], state=Invoice.STATES.ISSUED,
                          proforma=None, issue_date=test_date, customer=customers[1])


@pytest.fixture()
def transactions(customers, document_entries):
    test_date = datetime(2017, 9, 11, 10, 56, 24, 898509, pytz.UTC)
    test_amount = 10

    invoice = InvoiceFactory.create(invoice_entries=[document_entries[1], document_entries[2]],
                                    state=Invoice.STATES.ISSUED, proforma=None,
                                    customer=customers[2])
    TransactionFactory.create(state=Transaction.States.Settled, invoice=invoice,
                              payment_method__customer=invoice.customer, proforma=None,
                              created_at=test_date, amount=test_amount)
    test_date = test_date + timedelta(-50)
    test_amount = test_amount + 5

    invoice = InvoiceFactory.create(invoice_entries=[document_entries[2]],
                                    state=Invoice.STATES.ISSUED, proforma=None,
                                    customer=customers[1])
    TransactionFactory.create(state=Transaction.States.Settled, invoice=invoice,
                              payment_method__customer=invoice.customer, proforma=None,
                              created_at=test_date, amount=test_amount)
    test_amount = test_amount + 5

    invoice = InvoiceFactory.create(invoice_entries=[document_entries[1]],
                                    state=Invoice.STATES.ISSUED,
                                    proforma=None, customer=customers[2])
    TransactionFactory.create(state=Transaction.States.Settled, invoice=invoice,
                              payment_method__customer=invoice.customer, proforma=None,
                              created_at=test_date, amount=test_amount)

    invoice = InvoiceFactory.create(invoice_entries=[document_entries[2]],
                                    state=Invoice.STATES.ISSUED,
                                    proforma=None, customer=customers[1])
    TransactionFactory.create(state=Transaction.States.Settled, invoice=invoice,
                              payment_method__customer=invoice.customer, proforma=None,
                              created_at=test_date, amount=test_amount)
