---
title: Payment Methods in Silver
description: Detailed explanations of what is a Payment Method in Silver, how to retrieve and create one, as well as what does transitioning a Payment method means.
---
For resource definition check out [Resources](Resources#payment-method) page.

1. [List all customer's payment methods](#list-all-payment-methods)
2. [Retrieve a customer's payment method](#retrieve-a-specific-payment-method)
3. [Create a payment method](#create-a-payment-method)
4. [Transition a payment method](#transition-a-payment-method)

##### List all Payment Methods

```
GET /customers/<customer_id>/payment_methods/
```

Available filters: ---
<pre>

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
</pre>

##### Retrieve a specific Payment Method

```
GET /customers/<customer_id>/payment_methods/<payment_method_id>/
```
<pre>
    {
        "url": "http://127.0.0.1:8000/customers/1/payment_methods/2/",
        "transactions": "http://127.0.0.1:8000/customers/1/payment_methods/2/transactions/",
        "customer": "http://127.0.0.1:8000/customers/1/",
        "payment_processor": "http://127.0.0.1:8000/payment_processors/PayPal/",
        "added_at": "2016-12-17T15:11:03.008129Z",
        "verified_at": "2016-12-17T15:11:03.008129Z",
        "state": "enabled"
    }
</pre>

##### Create a Payment Method
```
POST /customers/<customer_id>/payment_methods/
```
<pre>
Payload:
    {
        "payment_processor": "http://127.0.0.1:8000/payment_processors/PayPal/",
        "state": "unverified",
        "additional_data": {
            "reference": "xoiy6c1b"
        }
    }
Response:
    HTTP 201 Created
    {
        "url": "http://127.0.0.1:8000/customers/1/payment_methods/2/",
        "transactions": "http://127.0.0.1:8000/customers/1/payment_methods/2/transactions/",
        "customer": "http://127.0.0.1:8000/customers/1/",
        "payment_processor": "http://127.0.0.1:8000/payment_processors/PayPal/",
        "added_at": "2016-12-17T15:11:03.008129Z",
        "verified_at": null,
        "state": "unverified"
    }
</pre>

_The `additional_data` field can be only specified for payments with `uninitialized` or `unverified` states, when transitioning to a `unverified` or a `enabled` state. The `additional_data` field will be passed to the Payment Processor's `initialize_unverified` or `initialize_enabled` methods._  

##### Transition a Payment Method
```
PATCH /customers/<customer_id>/payment_methods/<payment_method_id>/
```
<pre>
Payload:
    {
        "state": "enabled",
        "additional_data": {
            "reference": "xoiy6c1b"
        }
    }
Response:
    HTTP 200 OK
    {
        "url": "http://127.0.0.1:8000/customers/1/payment_methods/2/",
        "transactions": "http://127.0.0.1:8000/customers/1/payment_methods/2/transactions/",
        "customer": "http://127.0.0.1:8000/customers/1/",
        "payment_processor": "http://127.0.0.1:8000/payment_processors/PayPal/",
        "added_at": "2016-12-17T15:11:03.008129Z",
        "verified_at": null,
        "state": "enabled"
    }
</pre>
_The `additional_data` field can be only specified for payments with `uninitialized` or `unverified` states, when transitioning to a `unverified` or a `enabled` state. The `additional_data` field will be passed to the Payment Processor's `initialize_unverified` or `initialize_enabled` methods._  
