silver
======

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

TODO: Describe usage or point to docs. Also describe available settings and
templatetags.


Contribute
----------

If you want to contribute to this project, please perform the following steps

.. code-block:: bash

    # Fork this repository
    # Clone your fork
    mkvirtualenv -p python2.7 django-silver
    make develop

    git co -b feature_branch master
    # Implement your feature and tests
    git add . && git commit
    git push -u origin feature_branch
    # Send us a pull request for your feature branch
