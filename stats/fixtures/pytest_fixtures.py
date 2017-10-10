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


def create_customer():
    customers_list = []
    customers_list.append(CustomerFactory.create(first_name='Harry', last_name='Potter'))
    customers_list.append(CustomerFactory.create(first_name='Ron', last_name='Weasley'))
    customers_list.append(CustomerFactory.create(first_name='Hermione', last_name='Granger'))
    return customers_list


def create_document_entry():
    entries_list = []
    entries_list.append(DocumentEntryFactory(quantity=2, unit_price=100))
    entries_list.append(DocumentEntryFactory(quantity=1, unit_price=100))
    entries_list.append(DocumentEntryFactory(quantity=3, unit_price=100))
    return entries_list


def create_plan():
    plans_list = []
    provider = ProviderFactory.create(name='Presslabs')
    plans_list.append(PlanFactory.create(name='Oxygen', amount=150, currency='RON', provider=provider, generate_after=120))
    plans_list.append(PlanFactory.create(name='Hydrogen', amount=499, currency='USD', provider=provider, generate_after=120))
    plans_list.append(PlanFactory.create(name='Enterprise', amount=1999, currency='USD', provider=provider, generate_after=120))
    return plans_list


@pytest.fixture()
def create_subscription():
    test_date = datetime(2017, 9, 11, 10, 56, 24, 898509, pytz.UTC)
    test_amount = 10
    customers = create_customer()
    plans = create_plan()

    for i in range(7):
        subscription = SubscriptionFactory.create(
            plan=plans[i % 3],
            state=Subscription.STATES.ACTIVE,
            customer=customers[i % 2]
        )
        BillingLog.objects.create(subscription=subscription, billing_date=test_date,
                                  total=test_amount)
        BillingLog.objects.create(subscription=subscription, billing_date=test_date + timedelta(3),
                                  total=test_amount + 5)
        test_amount = test_amount + 10
        test_date = test_date + timedelta(-10)


@pytest.fixture()
def create_document():
    customers = create_customer()
    entries = create_document_entry()

    test_date = datetime(2017, 9, 11, 10, 56, 24, 898509, pytz.UTC)
    test_date = test_date + timedelta(-15)
    InvoiceFactory.create(invoice_entries=[entries[1]],
                          state=Invoice.STATES.ISSUED, proforma=None,
                          issue_date=test_date, customer=customers[0])

    test_date = test_date + timedelta(-15)
    InvoiceFactory.create(invoice_entries=[entries[0]],
                          state=Invoice.STATES.ISSUED, proforma=None,
                          issue_date=test_date, customer=customers[1])
    InvoiceFactory.create(invoice_entries=[entries[0]],
                          state=Invoice.STATES.ISSUED, proforma=None,
                          issue_date=test_date + timedelta(-4), customer=customers[1])

    test_date = test_date + timedelta(-15)
    InvoiceFactory.create(invoice_entries=[entries[2]],
                          state=Invoice.STATES.ISSUED, proforma=None,
                          issue_date=test_date, customer=customers[1])


@pytest.fixture()
def create_transaction():
    test_date = datetime(2017, 9, 11, 10, 56, 24, 898509, pytz.UTC)
    test_amount = 10
    entries = create_document_entry()
    customers = create_customer()

    invoice = InvoiceFactory.create(invoice_entries=[entries[1], entries[2]], state=Invoice.STATES.ISSUED,
                                    proforma=None, customer=customers[2])
    TransactionFactory.create(state=Transaction.States.Settled, invoice=invoice,
                              payment_method__customer=invoice.customer, proforma=None,
                              created_at=test_date, amount=test_amount)
    test_date = test_date + timedelta(-50)
    test_amount = test_amount + 5

    invoice = InvoiceFactory.create(invoice_entries=[entries[2]], state=Invoice.STATES.ISSUED,
                                    proforma=None, customer=customers[1])
    TransactionFactory.create(state=Transaction.States.Settled, invoice=invoice,
                              payment_method__customer=invoice.customer, proforma=None,
                              created_at=test_date, amount=test_amount)
    test_amount = test_amount + 5

    invoice = InvoiceFactory.create(invoice_entries=[entries[1]], state=Invoice.STATES.ISSUED,
                                    proforma=None, customer=customers[2])
    TransactionFactory.create(state=Transaction.States.Settled, invoice=invoice,
                              payment_method__customer=invoice.customer, proforma=None,
                              created_at=test_date, amount=test_amount)

    invoice = InvoiceFactory.create(invoice_entries=[entries[2]], state=Invoice.STATES.ISSUED,
                                    proforma=None, customer=customers[1])
    TransactionFactory.create(state=Transaction.States.Settled, invoice=invoice,
                              payment_method__customer=invoice.customer, proforma=None,
                              created_at=test_date, amount=test_amount)
