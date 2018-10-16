---
title: Plans in Silver
description: Here you will find what is a Plan in Silver, how to retrieve, update or disable one, as well as what are a plan's metered features and how to create them.
linktitle: Plans
categories: [silver]
keywords: [silver]
menu:
  docs:
    parent: "billing-units"
weight: 1
draft: false
aliases: []
toc: true
related: true
---

For resource definition check out the [Resources]({{< ref "../resources.md" >}}) page.

## List all plans

By default this will list every existing Plan.

``` http
GET /plans/  HTTP/1.1
```

Filters, such as `enabled` and `private`, can be used for better results. Available filters: `name`, `currency`, `enabled`, `private`, `interval`, `product_code` and `provider`.

``` http
GET /plans?enabled=True&private=False HTTP/1.1
```

## Create a plan

``` http
POST /plans HTTP/1.1
Content-Type: application/json

{
    "name": "Hydrogen",
    "interval": "month",
    "interval_count": 1,
    "amount": 150,
    "currency": "USD",
    "trial_period_days": 15,
    "metered_features": [
        {
            "name": "Page Views",
            "unit": "100k",
            "price_per_unit": 0.01,
            "included_units": 2.5,
            "product_code": "existing_pc_2"
        },
        {
            "name": "VIP Support",
            "price_per_unit": 49.99,
            "included_units": 1,
            "product_code": "non-existing_pc"
        }
    ],
    "due_days": 10,
    "generate_after": 86400,
    "product_code": "hyd_3g432556g",
    "enabled": true,
    "private": false,
    "provider": "www.example.com/providers/2/"
}
```

## Retrieve a plan

``` http
GET /plans/:id HTTP/1.1
```

## Update a plan

Only `name`, `generate_after` and `due_days` are editable through API.

``` http
PATCH /plans/:id HTTP/1.1
```

## Disable a plan

Plans cannot be actually deleted through API but only through the admin interface. They can be only disabled by API and this is what the `DELETE` verb should do.

``` http
DELETE /plans/:id HTTP/1.1
```

## List all metered features

``` http
GET /metered-features HTTP/1.1
```

## List the metered features of a plan

``` http
GET /plans/:id/metered-features HTTP/1.1
```

## Create a metered feature

``` http
POST /metered-features/ HTTP/1.1
Content-Type: application/json

{
  "name": "Random Metered Feature",
  "unit": "pounds",
  "price_per_unit": "100",
  "included_units": "2",
  "product_code": "Code"
}
```
