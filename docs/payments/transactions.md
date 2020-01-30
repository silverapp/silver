---
title: Transactions in silver
linktitle: Transactions
description: Detailed explanations of what is a Transaction in Silver, how to list all transactions or a specific one, as well as what does creating a transaction involves.
keywords: [silver]
menu:
  docs:
    parent: "payments"
---

For resource definition check out the [Resources](../silver-resources.md) page.

## List all Transactions

**Request**

``` http
GET /customers/<customer_id>/transactions/ HTTP/1.1
```

``` http
GET /customers/<customer_id>/payment_methods/<payment_method_id>/transactions/ HTTP/1.1
```

Available filters: `payment`, `is_usable`

**Response**

``` http
HTTP/1.1 200 OK
Content-Type: application/json

[
    {
        "id": "994e56ca-3340-449d-80d6-41d73446c0e6",
        "url": "http://127.0.0.1:8000/customers/2/transactions/994e56ca-3340-449d-80d6-41d73446c0e6/",
        "customer": "http://127.0.0.1:8000/customers/2/",
        "provider": "http://127.0.0.1:8000/providers/2/",
        "amount": "99.99",
        "currency": "USD",
        "state": "failed",
        "proforma": "http://127.0.0.1:8000/proformas/3/",
        "invoice": null,
        "can_be_consumed": false,
        "payment_processor": "braintree",
        "payment_method": "http://127.0.0.1:8000/customers/2/payment_methods/1/",
        "pay_url": "http://127.0.0.1:8000/pay/dfu9ANg0ajfja0gm9hj3m301dkcvwjgbqwe9/",
        "valid_until": null,
        "updated_at": "2018-01-22T10:00:22.636182Z",
        "created_at": "2018-01-22T10:00:10.515239Z",
        "fail_code": "insufficient_funds",
        "refund_code": null,
        "cancel_code": null
    },
    {
        "id": "994e56ca-3340-449d-80d6-41d73446c0e6",
        "url": "http://127.0.0.1:8000/customers/2/transactions/994e56ca-3340-449d-80d6-41d73446c0e6/",
        "customer": "http://127.0.0.1:8000/customers/2/",
        "provider": "http://127.0.0.1:8000/providers/2/",
        "amount": "99.99",
        "currency": "USD",
        "state": "settled",
        "proforma": "http://127.0.0.1:8000/proformas/3/",
        "invoice": null,
        "can_be_consumed": true,
        "payment_processor": "braintree",
        "payment_method": "http://127.0.0.1:8000/customers/2/payment_methods/1/",
        "pay_url": "http://127.0.0.1:8000/pay/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9/",
        "valid_until": null,
        "updated_at": "2018-01-23T10:00:22.636182Z",
        "created_at": "2018-01-23T10:00:10.515239Z",
        "fail_code": null,
        "refund_code": null,
        "cancel_code": null
    }
]
```

## Retrieve a specific Transaction

**Request**

``` http
GET /customers/<customer_id>/transactions/<transaction_uuid> HTTP/1.1
```

**Response**

``` http
HTTP/1.1 200 OK
Content-Type: application/json

{
    "id": "994e56ca-3340-449d-80d6-41d73446c0e6",
    "url": "http://127.0.0.1:8000/customers/2/transactions/994e56ca-3340-449d-80d6-41d73446c0e6/",
    "customer": "http://127.0.0.1:8000/customers/2/",
    "provider": "http://127.0.0.1:8000/providers/2/",
    "amount": "99.99",
    "currency": "USD",
    "state": "settled",
    "proforma": "http://127.0.0.1:8000/proformas/3/",
    "invoice": null,
    "can_be_consumed": true,
    "payment_processor": "braintree",
    "payment_method": "http://127.0.0.1:8000/customers/2/payment_methods/1/",
    "pay_url": "http://127.0.0.1:8000/pay/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9/",
    "valid_until": null,
    "updated_at": "2018-01-23T10:00:22.636182Z",
    "created_at": "2018-01-23T10:00:10.515239Z",
    "fail_code": null,
    "refund_code": null,
    "cancel_code": null
}
```

## Create a Transaction

**Request**

``` http
POST /customers/<customer_id>/transactions/ HTTP/1.1
Content-Type: application/json

{
    "payment_method": "http://127.0.0.1:8000/customers/2/payment_methods/1/",
    "amount": 99.99,
    "currency": "USD",
    "invoice": "http://127.0.0.1:8000/invoices/3/",
    "proforma": "http://127.0.0.1:8000/proformas/3/",
    "valid_until": "2018-01-23T10:00:10.515239Z",
}
```

* `amount`: Can be omitted, in which case the amount will be the remaining amount of the billing document to be paid. Otherwise it must be lower or equal to the remaining amount of the billing document to be paid.
* `currency`: Can be omitted, in which case the `transaction_currency` of the billing document will be used. If specified it must be the same as the `transaction_currency` of the billing document, so it can only be used as a safety measure.
* `invoice` and `proforma`: Only one of these must be specified for the transaction to be created. If both are specified, they must be related.
* `valid_until`: Can be omitted. If specified, the transaction cannot be paid by the customer past that date.

**Response**

``` http
HTTP/1.1 201 Created
Content-Type: application/json

{
    "id": "994e56ca-3340-449d-80d6-41d73446c0e6",
    "url": "http://127.0.0.1:8000/customers/2/transactions/994e56ca-3340-449d-80d6-41d73446c0e6/",
    "customer": "http://127.0.0.1:8000/customers/2/",
    "provider": "http://127.0.0.1:8000/providers/2/",
    "amount": "99.99",
    "currency": "USD",
    "state": "initial",
    "proforma": "http://127.0.0.1:8000/proformas/3/",
    "invoice": null,
    "can_be_consumed": true,
    "payment_processor": "braintree",
    "payment_method": "http://127.0.0.1:8000/customers/2/payment_methods/1/",
    "pay_url": "http://127.0.0.1:8000/pay/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9/",
    "valid_until": null,
    "updated_at": "2018-01-23T10:00:22.636182Z",
    "created_at": "2018-01-23T10:00:10.515239Z",
    "fail_code": null,
    "refund_code": null,
    "cancel_code": null
}
```
