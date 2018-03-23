---
title: Payment Processors in Silver
description: Detailed explanations of what is a Payment Processor in Silver, as well as how to list a provider's Payment Processors and how to retrieve a specific one.
---
For resource definition check out [Resources](Resources#payment-processor) page.

1. [List a Provider's Payment Processors](#list-a-providers-payment-processors)
2. [Retrieve a Provider's Payment Processor](#retrieve-a-providers-payment-processors)

##### List a Provider's Payment Processors

```
GET /providers/<provider_id>/payment_processors/
```

Available filters: `type`
<pre>
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
</pre>

##### Retrieve a specific Payment Method

```
GET /providers/<provider_id>/payment_processors/<payment_processor_id>/
```
<pre>
    {
        "name": "PayPal",
        "type": "triggered",
        "url": "http://127.0.0.1:8000/providers/1/payment_processors/PayPal/"
    }
</pre>
