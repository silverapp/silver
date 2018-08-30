---
title: Managing customers
description: An introduction to Silver's management of customers — how to retrieve a customer, filtering options, as well as create, update or delete operations.
---
For resource definition check out [Resources](Resources#customer) page.

1. [List all customers](#list-all-customers)
2. [Retrieve a customer](#retrieve-a-customer)
3. [Create new customer](#create-a-new-customer)
4. [Update a customer](#update-a-customer)
5. [Delete a customer](#delete-a-customer)

##### List all customers
By default this lists all the customers.
```
GET /customers
```
Available filtering parameters: `email`, `name`, `company`, `active`, `country`, `sales_tax_name`, `sales_tax_number`.
```
GET /customers?active=True
```
##### Retrieve a customer

```
GET /customers/:id
```

##### Create a new customer
<pre>
POST /customers
{
    'customer_reference': '5',
    '<b>name</b>': 'John Doe',
    'company': 'ACME Inc.',
    'email': 'johndoe@acme.inc',
    '<b>address_1</b>': 'Funny Road no.4',
    'address_2': null,
    'country': 'US',
    '<b>city</b>': 'Wilmington',
    'state': 'Delaware',
    'zip_code': 9000,
    'extra': 'Tax exempt due to XXX',
    'sales_tax_percent': 24,
    'sales_tax_name': 'VAT',
    'sales_tax_number': ''
    'consolidated_billing': true
}
</pre>

##### Update a customer
All the customer's fields are editable. Use `PATCH` for partial update and `PUT` for full update.
```
PATCH /customers/:id
PUT /customers/:id
```

##### Delete a customer
Customer deletion is actually a soft delete. Deleting a customer automatically cancels that customer's subscriptions.
```
DELETE /customers/:id
```
