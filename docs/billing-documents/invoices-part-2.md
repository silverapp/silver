---
title: Invoices in Silver - Part 2
description: Here you'll find all you need to know about how to update an invoice, how to modify/update/delete an entry, how to issue an invoice and how to pay or cancel one, as well as details about how automated invoices are generated.
linktitle: Invoices - Part 2
categories: [silver]
keywords: [silver]
menu:
  docs:
    parent: "billing-documents"
weight: 1
draft: false
aliases: ["billing-documents/invoices/"]
toc: true
related: true
---

## Update an invoice

> ###### NOTE
>
> Modifying an invoice is only possible when it's in `draft` state. Also, take note that the invoice state cannot be updated through this method.

Use `PATCH` for partial update and `PUT` for full update

``` http
PUT /invoices/:id HTTP/1.1
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
PATCH /invoices/:id HTTP/1.1
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

## Add an entry to an invoice

> ###### NOTE
>
> Adding an entry is only possible when the invoice is in `draft` state.

``` http
POST /invoices/:id/entries HTTP/1.1
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

## Update an entry of an invoice

> ###### NOTE
>
> Updating an entry is only possible when the invoice is in `draft` state.

``` http
PUT /invoices/:id/entries/:entry_id HTTP/1.1
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

## Delete an entry from an invoice

> ###### NOTE
>
> Deleting an entry is only possible when the invoice is in `draft` state.

``` http
DELETE /invoices/:id/entries/:entry_id HTTP/1.1
```

## Issue an invoice

``` http
PATCH /invoices/:id/state HTTP/1.1
Content-Type: application/json

{
  "state": "issued",
  "issue_date": "2014-10-01",
  "due_date": "2014-10-06"
}
```

The invoice must be in the `draft` state.
Issuing an invoice follows these steps:

* When `issue_date` is specified, the invoice's `issue_date` is set to this value. If it's not and the invoice has no `issue_date` set, it it set to the current date.
* If `due_date` is specified it overwrites the invoice's `due_date`
* If the invoice has no `billing_details` set, it copies the `billing_details` from the customer. The same goes with `sales_tax_percent` and `sales_tax_name`
* Sets the invoice status to `issued`

## Pay an invoice

``` http
PATCH /invoices/:id/state HTTP/1.1
Content-Type: application/json

{
    "state": "paid",
    "paid_date": "2014-10-04"
}
```

The invoice must be in the `issued` state.
Paying an invoice follows these steps:

* If `paid_date` is specified, set the invoice `paid_date` to this value, else set the invoice `paid_date` to the current date
* Sets the invoice status to `paid`

## Cancel an invoice

``` http
PATCH /invoices/:id/state HTTP/1.1
Content-Type: application/json

{
    "state": "canceled",
    "cancel_date": "2014-10-04"
}
```

The invoice must be in the `issued` state.
Canceling an invoice follows these steps:

* If `cancel_date` is specified, set the invoice `cancel_date` to this value, else set the invoice `cancel_date` to the current date
* Sets the invoice status to `paid`

## How automated invoices are generated

Each day a process runs and scans every active subscription. For each subscription schedules an invoicing job taking into account `generate_after`. The invoicing job has the following blueprint:

``` python
def invoicing(subscription, start_date, end_date):
```
