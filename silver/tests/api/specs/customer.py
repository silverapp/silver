
def spec_archived_customer(customer):
    return {
        'company': customer.company,
        'email': customer.email,
        'address_1': customer.address_1,
        'address_2': customer.address_2,
        'city': customer.city,
        'country': customer.country,
        'state': customer.state,
        'zip_code': customer.zip_code,
        'extra': customer.extra,
        'meta': customer.meta,
        'first_name': customer.first_name,
        'last_name': customer.last_name,
        'customer_reference': customer.customer_reference,
        'consolidated_billing': bool(customer.consolidated_billing),
        'payment_due_days': int(customer.payment_due_days),
        'sales_tax_number': customer.sales_tax_number,
        'sales_tax_percent': "%.2f" % customer.sales_tax_percent
    }
