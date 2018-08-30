---
title: Payments in Silver
description: An overview of what is a Payment in Silver, listing a customer's payments or retrieving a specific one, as well as creating and transitioning one.
---
For resource definition check out [Resources](Resources#payment) page.

1. [List a customer's Payments](#list-a-customers-payments)
2. [Retrieve a customer's payment](#retrieve-a-customers-payment)
3. [Create a payment](#create-a-payment)
4. [Transition a payment](#transition-a-payment)

##### List a Customer's Payments

```
GET /customers/<customer_id>/payments/
```

Available filters: `amount`, `currency`, `due_date`, `status`, `visible`, `provider`
<pre>
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
</pre>

##### Retrieve a Customer's Payment

```
GET /customers/<customer_id>/payments/<payment_id>/
```
<pre>
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
</pre>

##### Create a Payment
```
POST /customers/<customer_id>/payments/
```
<pre>
Payload:
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
Response:
    HTTP 201 Created
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
</pre>  

##### Transition a Payment
```
PATCH /customers/<customer_id>/payments/<payment_id>/
```
<pre>
Payload:
    {
        "status": "pending"
    }
Response:
    HTTP 200 OK
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
</pre>
_The `status` field is the only field that can be modified after the payment's creation. If there is an on-going transaction for this payment, then the payment cannot be modified._  
