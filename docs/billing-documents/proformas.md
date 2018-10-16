---
title: Proformas in Silver
description: Detailed explanations of what is a Proforma in Silver, how to create, delete and update one, as well as how to add entries. Also, it is explained the process of issuing and paying proformas.
linktitle: Proformas
categories: [silver]
keywords: [silver]
menu:
  docs:
    parent: "billing-documents"
weight: 1
draft: false
aliases: []
toc: true
related: true
---

For resource definition check out the [Resources]({{< ref "../resources.md" >}}) page.

## List all proformas

``` http
GET /proformas/ HTTP/1.1
```

Available filter parameters: `state`, `number`, `customer_name`, `customer_company`, `provider_name`, `provider_company`, `issue_date`, `due_date`, `paid_date`, `cancel_date`, `currency`, `sales_tax_name`.

## Retrieve a proforma

``` http
GET /proformas/:id HTTP/1.1
Content-Type: application/json

{
    "id": 1,
    "series": "pl",
    "number": 1,
    "provider": "https://api.example.com/providers/1/",
    "customer": "https://api.example.com/customers/1/",
    "archived_provider": {
        "city": "Timisoara",
        "name": "provider1",
        "display_email": "random@test.com",
        "extra": "",
        "country": "RO",
        "company": "",
        "state": "",
        "meta": null,
        "address_1": "Random address",
        "address_2": "",
        "notification_email": "random@test.com",
        "zip_code": "",
        "proforma_series": "pl"
    },
    "archived_customer": {
        "city": "Timisoara",
        "consolidated_billing": false,
        "extra": "",
        "country": "RO",
        "company": "",
        "sales_tax_percent": null,
        "state": "",
        "meta": null,
        "address_1": "adresa 1",
        "address_2": "",
        "payment_due_days": 5,
        "sales_tax_number": "",
        "zip_code": "",
        "customer_reference": "",
        "emails": [
            "[]"
        ],
        "name": "Gigel"
    },
    "due_date": "2016-12-11",
    "issue_date": "2016-12-06",
    "paid_date": null,
    "cancel_date": null,
    "sales_tax_name": "",
    "sales_tax_percent": null,
    "currency": "USD",
    "state": "issued",
    "invoice": null,
    "proforma_entries": [
        {
            "description": "pageviews description",
            "unit": "pageviews",
            "unit_price": "10.0000",
            "quantity": "1000.0000",
            "total": 10000.0,
            "total_before_tax": 10000.0,
            "start_date": null,
            "end_date": null,
            "prorated": true,
            "product_code": "pv"
        }
    ],
    "total": 10000.0,
    "pdf_url": "https://api.example.com/app_media/documents/provider1/proformas/2016/12/Proforma_pl-1.pdf",
    "transactions": [
        {
            "id": "adbc1b82-f89f-470a-9905-ad154a14764e",
            "url": "https://api.example.com/customers/1/transactions/adbc1b82-f89f-470a-9905-ad154a14764e/",
            "customer": "https://api.example.com/customers/1/",
            "provider": "https://api.example.com/providers/1/",
            "amount": "10000.00",
            "currency": "USD",
            "currency_rate_date": null,
            "state": "initial",
            "proforma": "https://api.example.com/proformas/1/",
            "invoice": null,
            "can_be_consumed": true,
            "payment_processor": "https://api.example.com/payment_processors/manual/",
            "payment_method": "https://api.example.com/customers/1/payment_methods/1/",
            "pay_url": "https://api.example.com/pay/adbc1b82-f89f-470a-9905-ad154a14764e/",
            "valid_until": null,
            "success_url": null,
            "failed_url": null
        },
        {
            "id": "d4ac558e-5e6f-460d-b89b-b5484f61d363",
            "url": "https://api.example.com/customers/1/transactions/d4ac558e-5e6f-460d-b89b-b5484f61d363/",
            "customer": "https://api.example.com/customers/1/",
            "provider": "https://api.example.com/providers/1/",
            "amount": "100.00",
            "currency": "USD",
            "currency_rate_date": null,
            "state": "initial",
            "proforma": "https://api.example.com/proformas/1/",
            "invoice": null,
            "can_be_consumed": true,
            "payment_processor": "https://api.example.com/payment_processors/braintree/",
            "payment_method": "https://api.example.com/customers/1/payment_methods/2/",
            "pay_url": "https://api.example.com/pay/d4ac558e-5e6f-460d-b89b-b5484f61d363/",
            "valid_until": null,
            "success_url": null,
            "failed_url": null
        }
    ]
}
```

## Create a proforma

``` http
PUT /proformas HTTP/1.1
Content-Type: application/json

{
  "due_date": "2014-10-06",
  "issue_date": "2014-10-01",
  "customer": "https://api.example.com/customers/32",
  "provider": "https://api.example.com/providers/45",
  "proforma_entries": [
      {
          "description": "Hydrogen Monthly Subscription for October 2014",
          "unit": "subscription",
          "quantity": 1,
          "unit_price": 150,
          "product_code": "hydrogen-subscription",
          "start_date": "2014-10-01",
          "end_date": "2014-10-31",
          "prorated": false
      },
      {
          "description": "Prorated PageViews for September 2014",
          "unit": "100k pageviews",
          "quantity": 5.4,
          "unit_price": 10,
          "product_code": "page-views",
          "start_date": "2014-09-16",
          "end_date": "2014-09-30",
          "prorated": true
      }
  ],
  "sales_tax_percent": 24,
  "sales_tax_name": "VAT",
  "currency": "USD",
  "state": "draft"
}
```

## Update a proforma

{{% note %}}
Modifying a proforma is only possible when it's in `draft` state. Also, take note that the proforma's state cannot be updated through this method.
{{% /note %}}

Use `PATCH` for partial update and `PUT` for full update

``` http
PUT /proformas/:id HTTP/1.1
Content-Type: application/json

{
  "due_date": "2014-10-06",
  "issue_date": "2014-10-01",
  "customer": "https://api.example.com/customers/32",
  "sales_tax_percent": 24,
  "sales_tax_name": "VAT",
  "currency": "USD"
}
```

``` http
PATCH /proformas/:id HTTP/1.1
Content-Type: application/json

{
  "due_date": "2014-10-06",
  "issue_date": "2014-10-01",
  "customer": "https://api.example.com/customers/32",
  "sales_tax_percent": 24,
  "sales_tax_name": "VAT",
  "currency": "USD"
}
```

## Add an entry to a proforma

{{% note %}}
Adding an entry is only possible when the proforma is in `draft` state.
{{% /note %}}

``` http
POST /proformas/:id/entries HTTP/1.1
Content-Type: application/json

{
  "description": "Hydrogen Monthly Subscription for October 2014",
  "unit": "subscription",
  "quantity": 1,
  "unit_price": 150,
  "product_code": "hydrogen-subscription",
  "start_date": "2014-10-01",
  "end_date": "2014-10-31",
  "prorated": false
}
```

## Update an entry of a proforma

{{% note %}}
Updating an entry is only possible when the proforma is in `draft` state.
{{% /note %}}

``` http
PUT /proformas/:id/entries/:entry_id HTTP/1.1
Content-Type: application/json

{
  "description": "Hydrogen Monthly Subscription for October 2014",
  "unit": "subscription",
  "quantity": 1,
  "unit_price": 150,
  "product_code": "hydrogen-subscription",
  "start_date": "2014-10-01",
  "end_date": "2014-10-31",
  "prorated": false
}
```

## Delete an entry from a proforma

{{% note %}}
Deleting an entry is only possible when the proforma is in `draft` state.
{{% /note %}}

``` http
DELETE /proformas/:id/entries/:entry_id HTTP/1.1
```

## Issue a proforma

The proforma must be in the `draft` state.
Issuing a proforma follows these steps:

* When `issue_date` is specified, the proforma's `issue_date` is set to this value. If it's not and the proforma has no `issue_date` set, it it set to the current date.
* If `due_date` is specified it overwrites the proforma's `due_date`
* If the proforma has no `billing_details` set, it copies the `billing_details` from the customer. The same goes with `sales_tax_percent` and `sales_tax_name`
* Sets the proforma status to `issued`

``` http
PATCH /proformas/:id/state HTTP/1.1
Content-Type: application/json

{
    "state": "issued",
    "issue_date": "2014-10-01",
    "due_date": "2014-10-06"
}
```

## Pay a proforma

The proforma must be in the `issued` state.
Paying a proforma follows these steps:

* If `paid_date` is specified, set the proforma `paid_date` to this value, else set the proforma `paid_date` to the current date
* Sets the proforma status to `paid`

{{% note %}}
if the provider's selected flow is `proforma`, when a proforma is paid, a proforma is issued and transitioned to `paid` state.
{{% /note %}}

``` http
PATCH /proformas/:id/state HTTP/1.1
Content-Type: application/json

{
  "state": "paid",
  "paid_date": "2014-10-04"
}
```

## Cancel a proforma
The proforma must be in the `issued` state.
Canceling an proforma follows these steps:

* If `cancel_date` is specified, set the proforma `cancel_date` to this value, else set the proforma `cancel_date` to the current date
* Sets the proforma status to `paid`

``` http
PATCH /proformas/:id/state HTTP/1.1
Content-Type: application/json

{
  "state": "canceled",
  "cancel_date": "2014-10-04"
}
```
