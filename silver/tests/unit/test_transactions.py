import pytest
from datetime import timedelta
from django.core.exceptions import ValidationError
from django.utils import timezone
from mock import patch

from silver.models import Transaction, Invoice
from silver.retry_patterns import RetryPatterns
from silver.tests.factories import TransactionFactory, PaymentMethodFactory, InvoiceFactory, \
    DocumentEntryFactory, ProviderFactory


@pytest.mark.django_db
def test_retry_transaction():
    payment_method = PaymentMethodFactory.create(verified=True, canceled=False)
    transaction = TransactionFactory.create(state=Transaction.States.Failed,
                                            payment_method=payment_method)

    assert transaction.retry()


@pytest.mark.django_db
def test_retry_already_retried_transaction():
    payment_method = PaymentMethodFactory.create(verified=True, canceled=False)
    transaction = TransactionFactory.create(state=Transaction.States.Failed,
                                            payment_method=payment_method)

    TransactionFactory.create(retried_transaction=transaction)

    with pytest.raises(ValidationError) as exception_info:
        transaction.retry()
    assert str(exception_info.value) == "[u'The transaction cannot be retried.']"


@pytest.mark.django_db
def test_retry_transaction_with_canceled_payment_method():
    payment_method = PaymentMethodFactory.create(verified=True, canceled=True)
    transaction = TransactionFactory.create(state=Transaction.States.Failed,
                                            payment_method=payment_method)

    with pytest.raises(ValidationError) as exception_info:
        transaction.retry()
    assert str(exception_info.value) == "{'payment_method': " \
                                        "[u'The payment method is not recurring.']}"


@pytest.mark.django_db
def test_retry_transaction_of_paid_billing_document():
    payment_method = PaymentMethodFactory.create(verified=True, canceled=False)

    invoice = InvoiceFactory.create(customer=payment_method.customer, state=Invoice.STATES.ISSUED)
    transaction = TransactionFactory.create(state=Transaction.States.Failed,
                                            payment_method=payment_method,
                                            invoice=invoice)

    invoice.pay()

    with pytest.raises(ValidationError) as exception_info:
        transaction.retry()
    assert str(exception_info.value) == "[u'The transaction cannot be retried.']"


@pytest.mark.django_db
def test_retry_transaction_of_canceled_billing_document():
    payment_method = PaymentMethodFactory.create(verified=True, canceled=False)

    invoice = InvoiceFactory.create(customer=payment_method.customer, state=Invoice.STATES.ISSUED)
    transaction = TransactionFactory.create(state=Transaction.States.Failed,
                                            payment_method=payment_method,
                                            invoice=invoice)

    invoice.cancel()

    with pytest.raises(ValidationError) as exception_info:
        transaction.retry()
    assert str(exception_info.value) == "[u'The transaction cannot be retried.']"


@pytest.mark.django_db
def test_retry_transaction_with_amount_greater_than_remaining_payable_amount():
    payment_method = PaymentMethodFactory.create(verified=True, canceled=False)

    entry = DocumentEntryFactory(quantity=1, unit_price=200)
    invoice = InvoiceFactory.create(customer=payment_method.customer, state=Invoice.STATES.ISSUED,
                                    invoice_entries=[entry])

    transaction = TransactionFactory.create(state=Transaction.States.Failed,
                                            payment_method=payment_method,
                                            invoice=invoice, amount=150)

    TransactionFactory.create(state=Transaction.States.Settled,
                              payment_method=payment_method,
                              invoice=invoice, amount=100)

    with pytest.raises(ValidationError) as exception_info:
        transaction.retry()
    assert str(exception_info.value) == "{'__all__': [u'Amount is greater than what should be " \
                                        "charged in order to pay the billing document.']}"


@pytest.mark.parametrize('state', [Transaction.States.Initial,
                                   Transaction.States.Pending,
                                   Transaction.States.Refunded,
                                   Transaction.States.Settled])
@pytest.mark.django_db
def test_retry_non_failed_transaction(state):
    payment_method = PaymentMethodFactory.create(verified=True, canceled=False)

    transaction = TransactionFactory.create(state=state, payment_method=payment_method)

    with pytest.raises(ValidationError) as exception_info:
        transaction.retry()
    assert str(exception_info.value) == "[u'The transaction cannot be retried.']"


@pytest.mark.django_db
def test_automatic_retries_count():
    transaction = TransactionFactory.create(state=Transaction.States.Failed)
    assert transaction.automatic_retries_count == 0

    automatic_retrial = TransactionFactory.create(state=Transaction.States.Failed,
                                                  retried_transaction=transaction,
                                                  retrial_type=Transaction.RetryTypes.Automatic)

    assert automatic_retrial.automatic_retries_count == 1

    staff_retrial = TransactionFactory.create(state=Transaction.States.Failed,
                                              retried_transaction=automatic_retrial,
                                              retrial_type=Transaction.RetryTypes.Staff)

    assert staff_retrial.automatic_retries_count == 1

    last_automatic_retrial = TransactionFactory.create(
        state=Transaction.States.Failed,
        retried_transaction=staff_retrial,
        retrial_type=Transaction.RetryTypes.Automatic
    )

    assert last_automatic_retrial.automatic_retries_count == 2


@pytest.mark.django_db
def test_next_retry_datetime_daily(monkeypatch):
    payment_method = PaymentMethodFactory.create(verified=True, canceled=False)

    provider = ProviderFactory.create(transaction_retry_pattern='daily')

    transaction = TransactionFactory.create(state=Transaction.States.Failed,
                                            payment_method=payment_method)

    monkeypatch.setattr('silver.models.Transaction.provider', provider)
    monkeypatch.setattr('silver.models.Transaction.automatic_retries_count', 3)

    assert transaction.next_retry_datetime == transaction.created_at + timedelta(days=1)


@pytest.mark.django_db
def test_next_retry_datetime_exponential(monkeypatch):
    payment_method = PaymentMethodFactory.create(verified=True, canceled=False)

    provider = ProviderFactory.create(transaction_retry_pattern='exponential')

    transaction = TransactionFactory.create(state=Transaction.States.Failed,
                                            payment_method=payment_method)

    monkeypatch.setattr('silver.models.Transaction.provider', provider)
    monkeypatch.setattr('silver.models.Transaction.automatic_retries_count', 3)

    # 2 ** 3 = 8
    assert transaction.next_retry_datetime == transaction.created_at + timedelta(days=8)


@pytest.mark.django_db
def test_next_retry_datetime_fibonacci(monkeypatch):
    payment_method = PaymentMethodFactory.create(verified=True, canceled=False)

    provider = ProviderFactory.create(transaction_retry_pattern='fibonacci')

    transaction = TransactionFactory.create(state=Transaction.States.Failed,
                                            payment_method=payment_method)

    monkeypatch.setattr('silver.models.Transaction.provider', provider)
    monkeypatch.setattr('silver.models.Transaction.automatic_retries_count', 3)

    # the 3rd number of the fibonacci series is 2
    assert transaction.next_retry_datetime == transaction.created_at + timedelta(days=2)


@pytest.mark.django_db
def test_should_be_automatically_retried(monkeypatch):
    transaction = TransactionFactory.create(created_at=timezone.now() - timedelta(days=1))

    monkeypatch.setattr('silver.models.Transaction.can_be_retried', True)
    monkeypatch.setattr('silver.models.Transaction.automatic_retries_count',
                        transaction.provider.transaction_maximum_automatic_retries)
    assert not transaction.should_be_automatically_retried

    monkeypatch.setattr('silver.models.Transaction.automatic_retries_count', 0)
    monkeypatch.setattr('silver.models.Transaction.next_retry_datetime',
                        timezone.now() + timedelta(days=1))
    assert not transaction.should_be_automatically_retried

    monkeypatch.setattr('silver.models.Transaction.next_retry_datetime', timezone.now())
    monkeypatch.setattr('silver.models.Transaction.can_be_retried', False)
    assert not transaction.should_be_automatically_retried

    monkeypatch.setattr('silver.models.Transaction.can_be_retried', True)
    assert transaction.should_be_automatically_retried
