---
title: How to install and configure Silver
description: Here are the required steps to install silver on your machine.
linktitle: Install and configure Silver
categories: [silver]
keywords: [silver]
menu:
  docs:
    parent: "silver"
weight: 2
draft: false
aliases: []
toc: true
related: true
---


## Install

Install the dependencies and the package itself.

```bash
sudo apt-get build-dep python-imaging
pip install django-silver
```

## Configure

Add the following to your project settings file

```
INSTALLED_APPS = (
    ...,
    'silver',
    ...
    )
```

Silver is now ready to be used in your application.

## Get started with silver

1. Create your profile as a service provider
2. Add your pricing plans to the mix
3. Import/add your customers
4. Create subscriptions to the desired plans for your customers
5.Create your custom templates using HTML/CSS or use the ones already provided
6. Generate the invoices, manually for the first time.
7. Lay back for the next billing cycle if you've added billing generation in a cron.
