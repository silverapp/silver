from django.utils.six import text_type


def spec_archived_provider(provider):
    return {
        'company': text_type(provider.company),
        'email': text_type(provider.email),
        'address_1': text_type(provider.address_1),
        'address_2': text_type(provider.address_2),
        'city': text_type(provider.city),
        'country': text_type(provider.country),
        'state': text_type(provider.state),
        'zip_code': text_type(provider.zip_code),
        'extra': text_type(provider.extra),
        'meta': provider.meta,
        'name': text_type(provider.name),
        'invoice_series': text_type(provider.invoice_series),
        'proforma_series': text_type(provider.proforma_series),
    }
