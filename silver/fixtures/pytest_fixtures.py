import factory
import pytest


@pytest.fixture()
def user(db, django_user_model):
    return django_user_model.objects.create(username='user')


@pytest.fixture()
def anonymous_api_client():
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture()
def authenticated_api_client(user):
    from silver.tests.api.utils.client import JSONApiClient

    client = JSONApiClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture()
def authenticated_client(user, client):
    user.set_password("password")
    user.save()

    client.login(username=user.username, password="password")

    return client


@pytest.fixture()
def customer(db):
    from silver.fixtures.factories import CustomerFactory

    return CustomerFactory.create()


@pytest.fixture()
def provider(db):
    from silver.fixtures.factories import ProviderFactory

    return ProviderFactory.create()


@pytest.fixture()
def invoice(db):
    from silver.fixtures.factories import InvoiceFactory

    return InvoiceFactory.create()


@pytest.fixture()
def issued_invoice(db):
    from silver.models import Invoice
    from silver.fixtures.factories import InvoiceFactory

    return InvoiceFactory.create(state=Invoice.STATES.ISSUED)


@pytest.fixture()
def two_pages_of_invoices(db, settings):
    from silver.models import Invoice
    from silver.fixtures.factories import InvoiceFactory

    allowed_states = [Invoice.STATES.ISSUED, Invoice.STATES.PAID, Invoice.STATES.CANCELED]
    return InvoiceFactory.create_batch(
        settings.API_PAGE_SIZE * 2,
        state=factory.Sequence(
            lambda n: allowed_states[n % len(allowed_states)]
        )
    )
