---
title: Providers in Silver
description: An overview of Providers in Silver, with details regarding listing all providers or a specific one, as well as how to create, update or delete one.
linktitle: Providers
categories: [silver]
keywords: [silver]
menu:
  docs:
    parent: "billing-entities"
weight: 1
draft: false
aliases: []
toc: true
related: true
---

For resource definition check out the [Resources]({{< ref "../resources.md" >}}) page.

## List all providers

By default this will list all the providers.

``` http
GET /providers/ HTTP/1.1
```

Filters can be used for better results. The available filters are `company` and `email`

``` http
GET /providers/?company=Presslabs HTTP/1.1
```

## List a specific provider

By default this will list a specific provider.

``` http
GET /providers/:id/ HTTP/1.1
```

## Create a new provider

``` http
POST /providers HTTP/1.1
Content-Type: application/json

{
  "name": "Presslabs",
  "company": "Presslabs SRL",
  "email": "contact@presslabs.com",
  "address_1": "Str. Vasile Alecsandri nr. 3, Etaj 3, Ap. 12 Timișoara,",
  "address_2": null,
  "country": "RO",
  "city": "Timisoara",
  "state": "Timis",
  "zip_code": 300566,
  "extra": "This can be used as an additional field to include into billing documents",
  "flow": "proforma",
  "invoice_series": "IS1",
  "invoice_starting_number": "1",
  "proforma_series": "PS1",
  "proforma_starting_number": "1",
  "default_document_state": "draft",
  "meta": ""
}
```

## Update a provider

All the provider's fields are editable. Use `PATCH` for partial updates and `PUT` for full updates.

``` http
PATCH /providers/:id HTTP/1.1
```

``` http
PUT /providers/:id HTTP/1.1
```

## Delete a provider

Provider deletion is actually a soft delete.

``` http
DELETE /providers/:id HTTP/1.1
```
