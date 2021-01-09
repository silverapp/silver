

def spec_archived_provider(provider):
    return {
        'company': provider.company,
        'email': provider.email,
        'address_1': provider.address_1,
        'address_2': provider.address_2,
        'city': provider.city,
        'country': provider.country,
        'state': provider.state,
        'zip_code': provider.zip_code,
        'extra': provider.extra,
        'meta': provider.meta,
        'name': provider.name,
        'invoice_series': provider.invoice_series,
        'proforma_series': provider.proforma_series,
    }
