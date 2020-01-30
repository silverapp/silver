---
title: Managing customers
linktitle: Customers
description: An introduction to Silver's management of customers — how to retrieve a customer, filtering options, as well as create, update or delete operations.
keywords: [silver]
menu:
  global:
    parent: "billing-entities"
---

For resource definition check out the [Resources](../silver-resources.md) page.

## List all customers

By default this lists all the customers.

``` http
GET /customers HTTP/1.1
```

Available filtering parameters: `email`, `name`, `company`, `active`, `country`, `sales_tax_name`, `sales_tax_number`.

``` http
GET /customers?active=True  HTTP/1.1
```

## Retrieve a customer

``` http
GET /customers/:id  HTTP/1.1
```

## Create a new customer

``` http
POST /customers HTTP/1.1
Content-Type: application/json

{
  "customer_reference": "5",
  "first_name": "John",
  "last_name": "Doe",
  "company": "ACME Inc.",
  "email": "johndoe@acme.inc",
  "address_1": "Funny Road no.4",
  "address_2": null,
  "country": "US",
  "city": "Wilmington",
  "state": "Delaware",
  "zip_code": 9000,
  "extra": "Tax exempt due to XXX",
  "sales_tax_percent": 24,
  "sales_tax_name": "VAT",
  "sales_tax_number": "",
  "consolidated_billing": true
}
```

## Update a customer

All the customer's fields are editable. Use `PATCH` for partial update and `PUT` for full update.

``` http
PATCH /customers/:id HTTP/1.1
```
``` http
PUT /customers/:id HTTP/1.1
```

## Delete a customer

Customer deletion is actually a soft delete. Deleting a customer automatically cancels that customer's subscriptions.

``` http
DELETE /customers/:id HTTP/1.1
```
