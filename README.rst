silver 
======

.. image:: https://drone.presslabs.net/api/badges/PressLabs/silver/status.svg?branch=master
   :target: https://drone.presslabs.net/PressLabs/silver

Django automated billing with an API

Installation
------------

To get the latest stable release from PyPi

.. code-block:: bash

    pip install django-silver

To get the latest commit from GitHub

.. code-block:: bash

    pip install -e git+git://github.com/PressLabs/silver.git#egg=silver

Add ``silver`` to your ``INSTALLED_APPS``

.. code-block:: python

    INSTALLED_APPS = (
        ...,
        'silver',
    )

Add the ``silver`` URLs to your ``urls.py``

.. code-block:: python

    urlpatterns = patterns('',
        ...
        url(r'^silver/', include('silver.urls')),
    )

Don't forget to migrate your database

.. code-block:: bash

    ./manage.py migrate silver


Usage
-----

For creating the PDF templates, Silver uses the [built-in templating engine of
Django] (https://docs.djangoproject.com/en/1.8/topics/templates/#the-django-template-language). 
The template variables that are available in the context of the template are:

    * `name`
    * `unit`
    * `subscription`
    * `plan`
    * `provider`
    * `customer`
    * `product_code`
    * `start_date`
    * `end_date`
    * `prorated`
    * `proration_percentage`
    * `metered_feature`
    * `context`

For the API reference, [check the wiki](https://github.com/PressLabs/silver/wiki)

TODO: Describe usage or point to docs. Also describe available settings and
templatetags.


Contribute
----------

Development of gitfs happens at http://github.com/PressLabs/silver.

Issues are tracked at http://github.com/PressLabs/silver/issues.

Python package can be found at https://pypi.python.org/pypi/django-silver/.

You are highly encouraged to contribute with code, tests, documentation or just
sharing experience.

Please see [CONTRIBUTING.md](CONTRIBUTING.md).
