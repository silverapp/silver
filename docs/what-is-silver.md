---
title: Silver
linktitle: What is Silver
description: Silver is a service for automatic billing. It assigns customers to plans and creates automatic invoice entries.
categories: [silver]
keywords: [silver]
weight: 1
draft: false
aliases: []
toc: true
related: true
slug: what-is-silver
---

## What’s its purpose?

Silver is an automatic billing app for Django. Silver elegantly handles "telco" billing processes like multiple pricing plans management, automatic bill aggregation, and generation.

## How the idea came up

Silver has been developed from scratch to handle WordPress hosting billing at Presslabs, as external services were too costly and other existing modules proved too complex to adapt to basic telco needs.

## Features

### Automated Billing
Adding a cron job will trigger invoice generation for your customers.

### Consolidated billing
Silver generates a single invoice for all the subscriptions of a customers.

### Multiple invoicing workflows

Are you using for example proforma invoices or just invoices? No problem. Silver can handle both.

### Administration panel

Use the intuitive Django admin panel to gain fine-grained control on the data stored in Silver.

### PDF templates created using HTML and CSS

Use the ubiquitous HTML and CSS to create highly-customisable and beautiful templates for your invoices.

### RESTful API and REST hooks

Clean, fully tested and fully documented RESTful API for easy integration with other (micro)services.

### On or off-premises document storage

Local, Amazon S3, Azure Storage, Rackspace CloudFiles, etc. Tell Silver your preferences in settings.py and it will comply.

### Easy to integrate with other Django-based applications

Just install it by using pip, add it to the INSTALLED_APPS setting and you are ready to go.

## How to contribute

Development of Silver happens on GitHub at http://github.com/silverapp/silver.

Issues are tracked at http://github.com/silverapp/silver/issues.

The Python package can be found at https://pypi.python.org/pypi/django-silver/.

You are highly encouraged to contribute with code, tests, documentation
or just sharing experience.

Please see CONTRIBUTING.md for a short guide on how to get started with
Silver contributions.
