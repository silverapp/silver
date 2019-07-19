---
title: Proformas in Silver - Part 2
description: Here you'll find all you need to know about how to update a proforma, how to modify/update/delete an entry, how to issue a proforma and how to pay or cancel one, as well as details about how automated proformas are generated.
linktitle: Proformas - Part 2
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

## Update a proforma

> ###### NOTE
>
> Modifying a proforma is only possible when it's in `draft` state. Also, take note that the proforma's state cannot be updated through this method.

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

> ###### NOTE
>
> Adding an entry is only possible when the proforma is in `draft` state.

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

> ###### NOTE
>
> Updating an entry is only possible when the proforma is in `draft` state.

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

> ###### NOTE
>
> Deleting an entry is only possible when the proforma is in `draft` state.

``` http
DELETE /proformas/:id/entries/:entry_id HTTP/1.1
```

## Issue a proforma

``` http
PATCH /proformas/:id/state HTTP/1.1
Content-Type: application/json

{
    "state": "issued",
    "issue_date": "2014-10-01",
    "due_date": "2014-10-06"
}
```

The proforma must be in the `draft` state.
Issuing a proforma follows these steps:

* When `issue_date` is specified, the proforma's `issue_date` is set to this value. If it's not and the proforma has no `issue_date` set, it it set to the current date.
* If `due_date` is specified it overwrites the proforma's `due_date`
* If the proforma has no `billing_details` set, it copies the `billing_details` from the customer. The same goes with `sales_tax_percent` and `sales_tax_name`
* Sets the proforma status to `issued`

## Pay a proforma

``` http
PATCH /proformas/:id/state HTTP/1.1
Content-Type: application/json

{
  "state": "paid",
  "paid_date": "2014-10-04"
}
```

The proforma must be in the `issued` state.
Paying a proforma follows these steps:

* If `paid_date` is specified, set the proforma `paid_date` to this value, else set the proforma `paid_date` to the current date
* Sets the proforma status to `paid`

> ###### NOTE
>
> If the provider's selected flow is `proforma`, when a proforma is paid, a proforma is issued and transitioned to `paid` state.

## Cancel a proforma

``` http
PATCH /proformas/:id/state HTTP/1.1
Content-Type: application/json

{
  "state": "canceled",
  "cancel_date": "2014-10-04"
}
```

The proforma must be in the `issued` state.
Canceling an proforma follows these steps:

* If `cancel_date` is specified, set the proforma `cancel_date` to this value, else set the proforma `cancel_date` to the current date
* Sets the proforma status to `paid`
