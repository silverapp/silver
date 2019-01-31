import factory
import pytest

from rest_framework.test import APIClient

from django.conf import settings as django_settings
from django.contrib.auth import get_user_model
from django.test import Client

from silver.models import Invoice
from silver.fixtures.factories import CustomerFactory, ProviderFactory, InvoiceFactory
from silver.tests.api.utils.client import JSONApiClient

User = get_user_model()


@pytest.fixture()
def settings():
    return django_settings


@pytest.fixture()
def user(db):
    return User.objects.create(username='user')


@pytest.fixture()
def anonymous_api_client():
    return APIClient()


@pytest.fixture()
def authenticated_api_client(user):
    client = JSONApiClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture()
def authenticated_client(user):
    user.set_password("password")
    user.save()

    client = Client()
    client.login(username=user.username, password="password")

    return client


@pytest.fixture()
def customer(db):
    return CustomerFactory.create()


@pytest.fixture()
def provider(db):
    return ProviderFactory.create()


@pytest.fixture()
def invoice(db):
    return InvoiceFactory.create()


@pytest.fixture()
def issued_invoice(db):
    return InvoiceFactory.create(state=Invoice.STATES.ISSUED)


@pytest.fixture()
def two_pages_of_invoices(db, settings):
    allowed_states = [Invoice.STATES.ISSUED, Invoice.STATES.PAID, Invoice.STATES.CANCELED]
    return InvoiceFactory.create_batch(
        settings.API_PAGE_SIZE * 2,
        state=factory.Sequence(
            lambda n: allowed_states[n % len(allowed_states)]
        )
    )
