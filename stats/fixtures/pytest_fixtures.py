import pytest
from datetime import datetime, timedelta

import pytz
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
def create_subscription_and_billing_log():
    test_date = datetime(2017, 9, 11, 10, 56, 24, 898509, pytz.UTC)
    test_amount = 300

    provider = ProviderFactory.create(name='Presslabs')
    for i in range(3):
        customer = CustomerFactory.create()
        plan = PlanFactory.create(name='Oxygen',
                                  amount=test_amount + 500,
                                  currency='USD',
                                  provider=provider, generate_after=120)
        subscription = SubscriptionFactory.create(
            plan=plan,
            state=Subscription.STATES.ACTIVE,
            customer=customer
        )
        BillingLog.objects.create(subscription=subscription, billing_date=test_date,
                                  total=test_amount)
        test_amount = test_amount + 100
        test_date = test_date + timedelta(-15)

    for i in range(3):
        customer = CustomerFactory.create()
        plan = PlanFactory.create(name='Hydrogen',
                                  amount=test_amount + 500,
                                  currency='USD',
                                  provider=provider, generate_after=120)
        subscription = SubscriptionFactory.create(
            plan=plan,
            state=Subscription.STATES.ACTIVE,
            customer=customer
        )
        BillingLog.objects.create(subscription=subscription,
                                  billing_date=test_date + timedelta(-15),
                                  total=test_amount)
        test_amount = test_amount + 100


@pytest.fixture()
def create_document():
    test_date = datetime(2017, 9, 11, 10, 56, 24, 898509, pytz.UTC)
    for i in range(5):
        test_date = test_date + timedelta(-15)
        InvoiceFactory.create(invoice_entries=[DocumentEntryFactory.create()],
                              state=Invoice.STATES.ISSUED, proforma=None,
                              issue_date=test_date + timedelta(-15))


@pytest.fixture()
def create_transaction():
    test_date = datetime(2017, 9, 11, 10, 56, 24, 898509, pytz.UTC)
    test_amount = 4321

    for i in range(5):
        test_date = test_date + timedelta(-15)
        invoice = InvoiceFactory.create(invoice_entries=[DocumentEntryFactory.create()],
                                        state=Invoice.STATES.ISSUED, proforma=None)
        TransactionFactory.create(state=Transaction.States.Settled, invoice=invoice,
                                  payment_method__customer=invoice.customer, proforma=None,
                                  created_at=test_date, amount=test_amount)
        test_amount = test_amount + 1000
