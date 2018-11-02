# [silver](https://www.presslabs.com/code/silver/)

[![Build Status](https://travis-ci.org/silverapp/silver.svg?branch=master)](https://travis-ci.org/silverapp/silver)
[![Build Status](https://drone.presslabs.net/api/badges/silverapp/silver/status.svg?branch=master)](https://drone.presslabs.net/silverapp/silver)
[![FOSSA Status](https://app.fossa.io/api/projects/git%2Bgithub.com%2Fsilverapp%2Fsilver.svg?type=shield)](https://app.fossa.io/projects/git%2Bgithub.com%2Fsilverapp%2Fsilver?ref=badge_shield)

**A Django automated billing system with a REST API.**

Silver was developed by the awesome engineering team at
[Presslabs](https://www.presslabs.com/), a Managed WordPress Hosting
provider.

For more open-source projects, check [Presslabs Code](https://www.presslabs.org/).

### Installation

To get the latest stable release from PyPi

```bash
sudo apt-get build-dep python-imaging
pip install django-silver
```

To get the latest commit from GitHub

```bash
pip install -e git+git://github.com/silverapp/silver.git#egg=silver
```

Add `silver` to your `INSTALLED_APPS`

```python
INSTALLED_APPS = (
    # ...,
    'silver',
)
```

Add the `silver` URLs to your `urls.py`

```python
urlpatterns = patterns('',
    ...
    url(r'^silver/', include('silver.urls')),
)
```

Don't forget to migrate your database

```bash
./manage.py migrate silver
```

### Configuration

For the complete API reference, check the project's
[documentation](https://www.presslabs.org/silver/docs/.).

#### Automated tasks

To run Silver automatically you have two choices, although we really
recommend the first one. You can either:

-   Use Celery (4.x) and setup a celery-beat for the following tasks
    (recommended):

    -   silver.tasks.generate\_documents
    -   silver.tasks.generate\_pdfs
    -   silver.tasks.execute\_transactions (if making use of silver
        transactions)
    -   silver.tasks.fetch\_transactions\_status (if making use of
        silver transactions, for which the payment processor doesn't
        offer callbacks)

    Requirements: Celery-once is used to ensure that tasks are not
    queued more than once, so you can call them as often as you'd like.
    Redis is required by celery-once, so if you prefer not to use redis,
    you will have to write your own tasks.

-   Setup CRONs which call the following Django commands (e.g.
    `./manage.py generate_documents`):

    -   generate\_documents
    -   generate\_pdfs
    -   execute\_transactions (if making use of silver transactions)
    -   fetch\_transactions\_status (if making use of silver
        transactions, for which the payment processor doesn't offer
        callbacks)

    You'll have to make sure that each of these commands is not run more
    than once at a time.

#### Billing documents templates

For creating the PDF templates, Silver uses the built-in [templating
engine of Django](https://docs.djangoproject.com/en/1.8/topics/templates/#the-django-template-language).
The template variables that are available in the context of the template are:

> -   `name`
> -   `unit`
> -   `subscription`
> -   `plan`
> -   `provider`
> -   `customer`
> -   `product_code`
> -   `start_date`
> -   `end_date`
> -   `prorated`
> -   `proration_percentage`
> -   `metered_feature`
> -   `context`

For specifying the storage used add the `SILVER_DOCUMENT_STORAGE`
setting to your settings file. Example for storing the PDFs on S3:

```python
SILVER_DOCUMENT_STORAGE = (
    'storages.backends.s3boto.S3BotoStorage', [], {
        'bucket': 'THE-AWS-BUCKET',
        'access_key': 'YOUR-AWS-ACCESS-KEY',
        'secret_key': 'YOUR-AWS-SECRET-KEY',
        'acl': 'private',
        'calling_format': 'boto.s3.connection.OrdinaryCallingFormat'
    }
)
```

#### Payment Processors settings

[Here's an example](https://github.com/silverapp/silver-braintree) for how the `PAYMENT_PROCESSORS` 
Django setting should look like, for the Braintree payment processor:

```python
# put this in your settings.py
braintree_setup_data = {
    'environment': braintree.Environment.Production,
    'merchant_id': BRAINTREE_MERCHANT_ID,
    'public_key': BRAINTREE_PUBLIC_KEY,
    'private_key': BRAINTREE_PRIVATE_KEY
}

PAYMENT_PROCESSORS = {
    'braintree_triggered': {
        'class': 'silver_braintree.payment_processors.BraintreeTriggered',
        'setup_data': braintree_setup_data,
    },
    'braintree_recurring': {
        'class': 'silver_braintree.payment_processors.BraintreeTriggeredRecurring',
        'setup_data': braintree_setup_data,
    }
```

Current available payment processors for Silver are:

> -   Braintree - https://github.com/silverapp/silver-braintree
> -   PayU RO - https://github.com/silverapp/silver-payu

#### Other available settings

> -   `SILVER_DEFAULT_DUE_DAYS` - the default number of days until an
>     invoice is due for payment.
> -   `SILVER_DOCUMENT_PREFIX` - it gets prepended to the path of the
>     saved files. The default path of the documents is
>     `{prefix}{company}/{doc_type}/{date}/{filename}`
> -   `SILVER_PAYMENT_TOKEN_EXPIRATION` - decides for how long the
>     pay\_url of a transaction is available, before it needs to be
>     reobtained
> -   `SILVER_AUTOMATICALLY_CREATE_TRANSACTIONS` - automatically create
>     transactions when a billing document is issued, for recurring
>     payment methods

#### Other features

To add REST hooks to Silver you can install and configure the following
packages:

> -   https://github.com/PressLabs/django-rest-hooks-ng
> -   https://github.com/PressLabs/django-rest-hooks-delivery

### Getting Started

1.  Create your profile as a service provider.
2.  Add your pricing plans to the mix.
3.  Import/add your customer list.
4.  Create subscriptions for your customers.
5.  Create your custom templates using HTML/CSS or use the ones already
    provided.
6.  Setup cron job for generating the invoices automatically.
7.  Enjoy. Silver will automatically generate the invoices or proforma
    invoices based on your providers' configuration.

### Contribute

Development of silver happens at http://github.com/silverapp/silver.

Issues are tracked at http://github.com/silverapp/silver/issues.

The Python package can be found at https://pypi.python.org/pypi/django-silver/.

You are highly encouraged to contribute with code, tests, documentation
or just sharing experience.

Please see CONTRIBUTING.md for a short guide on how to get started with
Silver contributions.
