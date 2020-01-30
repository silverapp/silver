---
title: Payment Processors in Silver
linktitle: Payment Processors
description: Detailed explanations of what is a Payment Processor in Silver, as well as how to list a provider's Payment Processors and how to retrieve a specific one.
keywords: [silver]
menu:
  global:
    parent: "payments"
    weight: 1
---

For resource definition check out the [Resources](../silver-resources.md) page.

## List a Provider's Payment Processors

Available filters: `type`

``` http
GET /providers/<provider_id>/payment_processors/ HTTP/1.1
Content-Type: application/json

[
    {
        "name": "Manual",
        "type": "manual",
        "url": "http://127.0.0.1:8000/providers/1/payment_processors/Manual/"
    },
    {
        "name": "PayPal",
        "type": "triggered",
        "url": "http://127.0.0.1:8000/providers/1/payment_processors/PayPal/"
    }
]
```

## Retrieve a specific Payment Processor

``` http
GET /providers/<provider_id>/payment_processors/<payment_processor_id>/ HTTP/1.1
Content-Type: application/json

{
    "name": "PayPal",
    "type": "triggered",
    "url": "http://127.0.0.1:8000/providers/1/payment_processors/PayPal/"
}
```
