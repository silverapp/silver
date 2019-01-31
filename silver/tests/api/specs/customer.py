from decimal import Decimal

from django.utils.six import text_type

from silver.tests.api.specs.utils import text_type_or_none


def spec_archived_customer(customer):
    return {
        'company': text_type(customer.company),
        'email': text_type(customer.email),
        'address_1': text_type(customer.address_1),
        'address_2': text_type(customer.address_2),
        'city': text_type(customer.city),
        'country': text_type(customer.country),
        'state': text_type(customer.state),
        'zip_code': text_type(customer.zip_code),
        'extra': text_type(customer.extra),
        'meta': customer.meta,
        'first_name': text_type(customer.first_name),
        'last_name': text_type(customer.last_name),
        'customer_reference': text_type(customer.customer_reference),
        'consolidated_billing': bool(customer.consolidated_billing),
        'payment_due_days': int(customer.payment_due_days),
        'sales_tax_number': text_type_or_none(customer.sales_tax_number),
        'sales_tax_percent': "%.2f" % customer.sales_tax_percent
    }
