---
title: Payment Methods in Silver
description: Detailed explanations of what is a Payment Method in Silver, how to retrieve and create one, as well as what does transitioning a Payment method means.
linktitle: Payment Methods
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

## List all Payment Methods

Available filters:

``` http
GET /customers/<customer_id>/payment_methods/ HTTP/1.1
Content-Type: application/json

[
    {
        "url": "http://127.0.0.1:8000/customers/1/payment_methods/1/",
        "transactions": null,
        "customer": "http://127.0.0.1:8000/customers/1/",
        "payment_processor": "http://127.0.0.1:8000/payment_processors/Manual/",
        "added_at": "2016-11-09T12:36:41.008129Z",
        "verified_at": null,
        "state": "uninitialized"
    },
    {
        "url": "http://127.0.0.1:8000/customers/1/payment_methods/2/",
        "transactions": "http://127.0.0.1:8000/customers/1/payment_methods/2/transactions/",
        "customer": "http://127.0.0.1:8000/customers/1/",
        "payment_processor": "http://127.0.0.1:8000/payment_processors/PayPal/",
        "added_at": "2016-12-17T15:11:03.008129Z",
        "verified_at": "2016-12-17T15:11:03.008129Z",
        "state": "enabled"
    }
]
```

## Retrieve a specific Payment Method

``` http
GET /customers/<customer_id>/payment_methods/<payment_method_id>/ HTTP/1.1
Content-Type: application/json

{
    "url": "http://127.0.0.1:8000/customers/1/payment_methods/2/",
    "transactions": "http://127.0.0.1:8000/customers/1/payment_methods/2/transactions/",
    "customer": "http://127.0.0.1:8000/customers/1/",
    "payment_processor": "http://127.0.0.1:8000/payment_processors/PayPal/",
    "added_at": "2016-12-17T15:11:03.008129Z",
    "verified_at": "2016-12-17T15:11:03.008129Z",
    "state": "enabled"
}
```

## Create a Payment Method

Request:

``` http
POST /customers/<customer_id>/payment_methods/ HTTP/1.1
Content-Type: application/json

{
  "payment_processor": "http://127.0.0.1:8000/payment_processors/PayPal/",
  "state": "unverified",
  "additional_data": {
    "reference": "xoiy6c1b"
  }
}
```

Response:

``` http
HTTP/1.1 201 Created
Content-Type: application/json

{
    "url": "http://127.0.0.1:8000/customers/1/payment_methods/2/",
    "transactions": "http://127.0.0.1:8000/customers/1/payment_methods/2/transactions/",
    "customer": "http://127.0.0.1:8000/customers/1/",
    "payment_processor": "http://127.0.0.1:8000/payment_processors/PayPal/",
    "added_at": "2016-12-17T15:11:03.008129Z",
    "verified_at": null,
    "state": "unverified"
}
```

The `additional_data` field can be only specified for payments with `uninitialized` or `unverified` states, when transitioning to a `unverified` or a `enabled` state. The `additional_data` field will be passed to the Payment Processor's `initialize_unverified` or `initialize_enabled` methods.

## Transition a Payment Method

Request:

``` http
PATCH /customers/<customer_id>/payment_methods/<payment_method_id>/ HTTP/1.1
Content-Type: application/json

{
    "state": "enabled",
    "additional_data": {
        "reference": "xoiy6c1b"
    }
}
```

Response:

``` http
HTTP/1.1 200 OK
Content-Type: application/json

{
    "url": "http://127.0.0.1:8000/customers/1/payment_methods/2/",
    "transactions": "http://127.0.0.1:8000/customers/1/payment_methods/2/transactions/",
    "customer": "http://127.0.0.1:8000/customers/1/",
    "payment_processor": "http://127.0.0.1:8000/payment_processors/PayPal/",
    "added_at": "2016-12-17T15:11:03.008129Z",
    "verified_at": null,
    "state": "enabled"
}
```

The `additional_data` field can be only specified for payments with `uninitialized` or `unverified` states, when transitioning to a `unverified` or a `enabled` state. The `additional_data` field will be passed to the Payment Processor's `initialize_unverified` or `initialize_enabled` methods.
