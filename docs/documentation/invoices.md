---
title: Invoices
description: Detailed explanations of what is an Invoice in Silver, how to create, delete and update one, as well as what does the process of paying an invoice involves.
---
For resource definition check out [Resources](Resources#invoice) page.

1. [List all invoices](#list-all-invoices)
2. [Retrieve an invoice](#retrieve-an-invoice)
3. [Create an invoice](#create-an-invoice)
4. [Update an invoice](#update-an-invoice)
5. [Add an entry to an invoice](#add-an-entry-to-an-invoice)
7. [Delete an entry from an invoice](#delete-an-entry-from-an-invoice)
8. [Update an entry of an invoice](#update-an-entry-of-an-invoice)
8. [Issue an invoice](#issue-an-invoice)
9. [Pay an invoice](#pay-an-invoice)
10. [Cancel an invoice](#cancel-an-invoice)

##### List all invoices

```
GET /invoices/

```

Available filter parameters: `state`, `number`, `customer_name`, `customer_company`, `provider_name`, `provider_company`, `issue_date`, `due_date`, `paid_date`, `cancel_date`, `currency`, `sales_tax_name`.

##### Retrieve an invoice

```
GET /invoices/:id
{
    "id": 1,
    "series": "pl",
    "number": 1,
    "provider": "https://api.example.com/providers/1/",
    "customer": "https://api.example.com/customers/1/",
    "archived_provider": {
        "city": "Timisoara",
        "name": "provider1",
        "display_email": "random@test.com",
        "extra": "",
        "country": "RO",
        "company": "",
        "state": "",
        "meta": null,
        "address_1": "Random address",
        "address_2": "",
        "notification_email": "random@test.com",
        "zip_code": "",
        "invoice_series": "pl"
    },
    "archived_customer": {
        "city": "Timisoara",
        "consolidated_billing": false,
        "extra": "",
        "country": "RO",
        "company": "",
        "sales_tax_percent": null,
        "state": "",
        "meta": null,
        "address_1": "adresa 1",
        "address_2": "",
        "payment_due_days": 5,
        "sales_tax_number": "",
        "zip_code": "",
        "customer_reference": "",
        "emails": [
            "[u'[]']"
        ],
        "name": "Gigel"
    },
    "due_date": "2017-01-04",
    "issue_date": "2017-01-04",
    "paid_date": "2017-01-04",
    "cancel_date": null,
    "sales_tax_name": "",
    "sales_tax_percent": null,
    "currency": "USD",
    "state": "paid",
    "proforma": "https://api.example.com/proformas/1/",
    "invoice_entries": [
        {
            "description": "pageviews description",
            "unit": "pageviews",
            "unit_price": "10.0000",
            "quantity": "1000.0000",
            "total": 10000.0,
            "total_before_tax": 10000.0,
            "start_date": null,
            "end_date": null,
            "prorated": true,
            "product_code": "pv"
        }
    ],
    "total": 10000.0,
    "pdf_url": "https://api.example.com/app_media/documents/provider1/invoices/2017/01/Invoice_pl-1.pdf",
    "transactions": [
        {
            "id": "8eb0e5a2-b5af-406e-9b77-b91a4a995cb5",
            "url": "https://api.example.com/customers/1/transactions/8eb0e5a2-b5af-406e-9b77-b91a4a995cb5/",
            "customer": "https://api.example.com/customers/1/",
            "provider": "https://api.example.com/providers/1/",
            "amount": "100.00",
            "currency": "USD",
            "currency_rate_date": null,
            "state": "initial",
            "proforma": null,
            "invoice": "https://api.example.com/invoices/1/",
            "can_be_consumed": true,
            "payment_processor": "https://api.example.com/payment_processors/manual/",
            "payment_method": "https://api.example.com/customers/1/payment_methods/1/",
            "pay_url": "https://api.example.com/pay/8eb0e5a2-b5af-406e-9b77-b91a4a995cb5/",
            "valid_until": null,
            "success_url": null,
            "failed_url": null
        }
    ]
}
```

##### Create an invoice
<pre>
PUT /invoices
{
    'due_date': '2014-10-06',
    'issue_date': '2014-10-01',
    '<b>customer</b>': 'https://api.example.com/customers/32',
    '<b>provider</b>': 'https://api.example.com/providers/45',
    '<b>invoice_entries</b>': [
        {
            'description': 'Hydrogen Monthly Subscription for October 2014',
            'unit': 'subscription',
            'quantity': 1,
            'unit_price': 150,
            'product_code': 'hydrogen-subscription',
            'start_date': '2014-10-01',
            'end_date': '2014-10-31',
            'prorated': False
        },
        {
            'description': 'Prorated PageViews for September 2014',
            'unit': '100k pageviews',
            'quantity': 5.4,
            'unit_price': 10,
            'product_code': 'page-views',
            'start_date': '2014-09-16',
            'end_date': '2014-09-30',
            'prorated': True
        }
    ]
    'sales_tax_percent': 24,
    'sales_tax_name': 'VAT',
    'currency': 'USD',
    'state': 'draft'
}
</pre>

##### Update an invoice
_NOTE_: Modifying an invoice is only possible when it's in `draft` state. Also, take note that the invoice state cannot be updated through this method.

Use `PATCH` for partial update and `PUT` for full update

```
PUT /invoices/:id
PATCH /invoices/:id
{
    'due_date': '2014-10-06',
    'issue_date': '2014-10-01',
    'customer': 'https://api.example.com/customers/32',
    'sales_tax_percent': 24,
    'sales_tax_name': 'VAT',
    'currency': 'USD'
}
```

##### Add an entry to an invoice
_NOTE_: Adding an entry is only possible when the invoice is in `draft` state.

<pre>
POST /invoices/:id/entries
{
    '<b>description</b>': 'Hydrogen Monthly Subscription for October 2014',
    'unit': 'subscription',
    '<b>quantity</b>': 1,
    '<b>unit_price</b>': 150,
    'product_code': 'hydrogen-subscription',
    'start_date': '2014-10-01',
    'end_date': '2014-10-31',
    'prorated': False
}
</pre>

##### Update an entry of an invoice
_NOTE_: Updating an entry is only possible when the invoice is in `draft` state.
```
PUT /invoices/:id/entries/:entry_id
{
    'description': 'Hydrogen Monthly Subscription for October 2014',
    'unit': 'subscription',
    'quantity': 1,
    'unit_price': 150,
    'product_code': 'hydrogen-subscription',
    'start_date': '2014-10-01',
    'end_date': '2014-10-31',
    'prorated': False
}
```

##### Delete an entry from an invoice
_NOTE_: Deleting an entry is only possible when the invoice is in `draft` state.
```
DELETE /invoices/:id/entries/:entry_id
```

##### Issue an invoice
The invoice must be in the `draft` state.
Issuing an invoice follows these steps:
* When `issue_date` is specified, the invoice's `issue_date` is set to this value. If it's not and the invoice has no `issue_date` set, it it set to the current date.
* If `due_date` is specified it overwrites the invoice's `due_date`
* If the invoice has no `billing_details` set, it copies the `billing_details` from the customer. The same goes with `sales_tax_percent` and `sales_tax_name`
* Sets the invoice status to `issued`

```
PATCH /invoices/:id/state
{
    'state': 'issued',
    'issue_date': '2014-10-01',
    'due_date': '2014-10-06'
}
```

##### Pay an invoice
The invoice must be in the `issued` state.
Paying an invoice follows these steps:
* If `paid_date` is specified, set the invoice `paid_date` to this value, else set the invoice `paid_date` to the current date
* Sets the invoice status to `paid`
```
PATCH /invoices/:id/state
{
    'state': 'paid',
    'paid_date': '2014-10-04'
}
```

##### Cancel an invoice
The invoice must be in the `issued` state.
Canceling an invoice follows these steps:
* If `cancel_date` is specified, set the invoice `cancel_date` to this value, else set the invoice `cancel_date` to the current date
* Sets the invoice status to `paid`
```
PATCH /invoices/:id/state
{
    'state': 'canceled',
    'cancel_date': '2014-10-04'
}
```
