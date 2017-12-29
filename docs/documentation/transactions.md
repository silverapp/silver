For resource definition check out [Resources](Resources#transactions) page.

1. [List all transactions](#list-all-transactions)
2. [Retrieve a transaction](#retrieve-a-specific-transaction)
3. [Create a transaction](#create-a-transaction)

##### List all Transactions

```
GET /customers/<customer_id>/payment_methods/<payment_method_id>/transactions/
GET /customers/<customer_id>/transactions/
```

Available filters: `payment`, `is_usable`
<pre>
[
    {
        "url": "http://127.0.0.1:8000/customers/1/transactions/d54ba7e0-ee95-4843-b2d8-62cc061bc688/",
        "payment_method": "http://127.0.0.1:8000/customers/1/payment_methods/1/",
        "payment": "http://127.0.0.1:8000/customers/1/payments/12/",
        "is_usable": true,
        "pay_url": "http://127.0.0.1:8000/pay/d54ba7e0-ee95-4843-b2d8-62cc061bc688/",
        "valid_until": null
    },
    {
        "url": "http://127.0.0.1:8000/customers/1/transactions/304d53d0-0d9d-48ff-9350-8f309ca22cf9/",
        "payment_method": "http://127.0.0.1:8000/customers/1/payment_methods/2/",
        "payment": "http://127.0.0.1:8000/customers/1/payments/16/",
        "is_usable": false,
        "pay_url": "http://127.0.0.1:8000/pay/304d53d0-0d9d-48ff-9350-8f309ca22cf9/",
        "valid_until": null
    }
]
</pre>

##### Retrieve a specific Transaction

```
GET /customers/<customer_id>/transactions/<transaction_uuid>
```
<pre>
    {
        "url": "http://127.0.0.1:8000/customers/1/transactions/304d53d0-0d9d-48ff-9350-8f309ca22cf9/",
        "payment_method": "http://127.0.0.1:8000/customers/1/payment_methods/2/",
        "payment": "http://127.0.0.1:8000/customers/1/payments/16/",
        "is_usable": false,
        "pay_url": "http://127.0.0.1:8000/pay/304d53d0-0d9d-48ff-9350-8f309ca22cf9/",
        "valid_until": "2015-10-22T19:50:08"
    }
</pre>

##### Create a Transaction
```
POST /customers/<customer_id>/payment_methods/<payment_method>/transactions/
```
<pre>
Payload:
    {
        "payment": "http://127.0.0.1:8000/customers/1/payments/16/",
        "valid_until": "2015-10-22T19:50:08"
    }
Response:
    HTTP 201 Created
    {
        "url": "http://127.0.0.1:8000/customers/1/transactions/304d53d0-0d9d-48ff-9350-8f309ca22cf9/",
        "payment_method": "http://127.0.0.1:8000/customers/1/payment_methods/2/",
        "payment": "http://127.0.0.1:8000/customers/1/payments/16/",
        "is_usable": false,
        "pay_url": "http://127.0.0.1:8000/pay/304d53d0-0d9d-48ff-9350-8f309ca22cf9/",
        "valid_until": "2015-10-22T19:50:08"
    }
</pre>
