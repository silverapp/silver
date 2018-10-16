---
title: Payments in Silver
description: An overview of what is a Payment in Silver, listing a customer's payments or retrieving a specific one, as well as creating and transitioning one.
linktitle: Payments
categories: [silver]
keywords: [silver]
menu:
  docs:
    parent: "payments"
weight: 1
draft: false
aliases: []
toc: true
related: true
---

For resource definition check out the [Resources]({{< ref "../resources.md" >}}) page.

## List a Customer's Payments

Available filters: `amount`, `currency`, `due_date`, `status`, `visible`, `provider`

``` http
GET /customers/<customer_id>/payments/ HTTP/1.1
Content-Type: application/json

[
    {
        "id": 1,
        "url": "http://127.0.0.1:8000/customers/1/payments/1/",
        "customer": "http://127.0.0.1:8000/customers/1/",
        "provider": "http://127.0.0.1:8000/providers/1/",
        "amount": "200.00",
        "currency": "USD",
        "due_date": null,
        "status": "unpaid",
        "visible": true,
        "proforma": null,
        "invoice": "http://127.0.0.1:8000/invoices/1/"
    },
    {...}
]
```

## Retrieve a Customer's Payment

``` http
GET /customers/<customer_id>/payments/<payment_id>/ HTTP/1.1
Content-Type: application/json

{
    "id": 1,
    "url": "http://127.0.0.1:8000/customers/1/payments/1/",
    "customer": "http://127.0.0.1:8000/customers/1/",
    "provider": "http://127.0.0.1:8000/providers/1/",
    "amount": "200.00",
    "currency": "USD",
    "due_date": null,
    "status": "unpaid",
    "visible": true,
    "proforma": null,
    "invoice": "http://127.0.0.1:8000/invoices/1/"
}
```

## Create a Payment

Request:

``` http
POST /customers/<customer_id>/payments/ HTTP/1.1
Content-Type: application/json

{
    "customer": "http://127.0.0.1:8000/customers/1/",
    "provider": "http://127.0.0.1:8000/providers/1/",
    "amount": "200.00",
    "currency": "USD",
    "due_date": null,
    "status": "unpaid",
    "visible": true,
    "proforma": "http://127.0.0.1:8000/proformas/1/",
    "invoice": "http://127.0.0.1:8000/invoices/1/"
}
```

Response:

``` http
HTTP/1.1 201 Created
Content-Type: application/json

{
    "id": 1,
    "url": "http://127.0.0.1:8000/customers/1/payments/1/",
    "customer": "http://127.0.0.1:8000/customers/1/",
    "provider": "http://127.0.0.1:8000/providers/1/",
    "amount": "200.00",
    "currency": "USD",
    "due_date": null,
    "status": "unpaid",
    "visible": true,
    "proforma": "http://127.0.0.1:8000/proformas/1/",
    "invoice": "http://127.0.0.1:8000/invoices/1/"
}
```

## Transition a Payment

Request:

``` http
PATCH /customers/<customer_id>/payments/<payment_id>/ HTTP/1.1
Content-Type: application/json

{
    "status": "pending"
}
```

Response:

``` http
HTTP/1.1 200 OK
Content-Type: application/json

{
    "id": 1,
    "url": "http://127.0.0.1:8000/customers/1/payments/1/",
    "customer": "http://127.0.0.1:8000/customers/1/",
    "provider": "http://127.0.0.1:8000/providers/1/",
    "amount": "200.00",
    "currency": "USD",
    "due_date": null,
    "status": "pending",
    "visible": true,
    "proforma": "http://127.0.0.1:8000/proformas/1/",
    "invoice": "http://127.0.0.1:8000/invoices/1/"
}
```

The `status` field is the only field that can be modified after the payment's creation. If there is an on-going transaction for this payment, then the payment cannot be modified.
