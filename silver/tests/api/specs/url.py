from rest_framework.reverse import reverse

from silver.tests.api.utils.path import absolute_url
from silver.utils.payments import _get_jwt_token


def spec_invoice_url(invoice):
    return absolute_url(reverse("invoice-detail", args=[invoice.id]))


def spec_proforma_url(proforma):
    return absolute_url(reverse("proforma-detail", args=[proforma.id]))


def spec_customer_url(customer):
    return absolute_url(reverse("customer-detail", args=[customer.id]))


def spec_provider_url(provider):
    return absolute_url(reverse("provider-detail", args=[provider.id]))


def spec_transaction_url(transaction):
    return absolute_url(reverse("transaction-detail", args=[transaction.customer.id,
                                                            transaction.uuid]))


def spec_transaction_pay_url(transaction):
    return absolute_url(reverse("payment", args=[_get_jwt_token(transaction)]))


def spec_payment_method_url(payment_method):
    return absolute_url(reverse("payment-method-detail", args=[payment_method.customer.id,
                                                               payment_method.id]))
