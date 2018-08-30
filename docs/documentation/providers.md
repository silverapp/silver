---
title: Providers in Silver
description: An overview of Providers in Silver, with details regarding listing all providers or a specific one, as well as how to create, update or delete one.
---
For resource definition check out [Resources](Resources#provider)  page.

1. [List all providers](#list-all-providers)
2. [List a specific provider](#list-a-specific-provider)
3. [Create a new provider](#create-a-new-provider)
4. [Update a provider](#update-a-provider)
5. [Delete a provider](#delete-a-provider)

##### List all providers
By default this will list all the providers.
```
GET /providers/
```
Filters can be used for better results. The available filters are `company` and `email`
```
GET /providers/?company=Presslabs
```

##### List a specific provider
By default this will list a specific provider.
```
GET /providers/:id/
```

##### Create a new provider
<pre>
POST /providers
{
    '<b>name</b>': 'Presslabs',
    'company': 'Presslabs SRL',
    'email': 'contact@presslabs.com',
    '<b>address_1</b>': 'Str. Vasile Alecsandri nr. 3, Etaj 3, Ap. 12 Timișoara,',
    'address_2': null,
    'country': 'RO',
    '<b>city</b>': 'Timisoara',
    'state': 'Timis',
    'zip_code': 300566,
    'extra': 'This can be used as an additional field to include into billing documents',
    'flow': 'proforma',
    '<b>invoice_series</b>': 'IS1',
    '<b>invoice_starting_number</b>': '1',
    'proforma_series': 'PS1',
    'proforma_starting_number': '1',
    'default_document_state': 'draft',
    'meta': ''
}
</pre>

##### Update a provider
All the provider's fields are editable. Use `PATCH` for partial updates and `PUT` for full updates.
```
PATCH /providers/:id
PUT /providers/:id
```

##### Delete a provider
Provider deletion is actually a soft delete.
```
DELETE /providers/:id
```
