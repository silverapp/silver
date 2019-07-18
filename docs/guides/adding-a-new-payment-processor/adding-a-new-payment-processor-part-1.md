---
title:  Part 1 - Create the payment processor and payment method
description: The first part of this tutorial will show you how to add a new payment processor to your app, details about its structure and how to implement a payment method class.
linktitle: Part 1 - Create the payment processor and payment method
categories: [silver]
keywords: [silver]
menu:
  docs:
    parent: "adding-a-new-payment-processor"
weight: 1
draft: false
aliases: []
toc: true
related: true
---

## Getting started

First, there needs to be a Python SDK for your Payment Processor, that allows you to connect and
communicate with its services. If there isn't one, you should start by contacting the Payment
Processor's developers and ask them if they can provide one, or try implementing it yourself.

In this guide, we'll name the SDK package `payment_processor_sdk` and it will be totally imaginary.
We could use a real SDK, but most have their quirks and ways of doing stuff, and that will only act
as a distraction. So you might consider also having a look at some real payment processor implementations
in [here](https://github.com/silverapp/).

It's usually best to have a separate Django app or project for your Payment Processor.
You may call your app / project whatever you want, but in this guide we'll name it `payment_processor`.
We'll also assume you've named your main Silver project `silver_project`. You should obviously use
proper names instead.


### The Django app variant

This method is better if you want to get started faster. You can always decide to publish your app
as a separate Django project if you want.

Create your app:

```bash
./manage.py startapp payment_processor
```

Add it to your INSTALLED_APPS in your settings file:

```python
INTERNAL_APPS = [
    'silver',
    'payment_processor',
    # ...
]
```

### The Django project variant
This method is better if you want to keep your projects separated or publish your work from the
beginning.

This method also assumes you have already created a virtualenv for the main project, the payment
processor project and installed Django there too.

Create your project:

```bash
django_admin startproject payment_processor
```

Install it by linking it inside your main project's environment, where Silver is also installed:

```bash
workon silver_project  # Change to your main project's environment
cd payment_processor  # Go to your payment_processor's directory
pip install -e .  # Install your payment_processor development project as a linked dependecy
```

Add the payment_processor to your INSTALLED_APPS in your silver_project's settings file:

```python
INTERNAL_APPS = [
    'silver',
    'payment_processor',
    # ...
]
```

## Deciding how your Payment Processor will look

In your payment_processor app you should have the following structure. It's fine if you can't find
everything in there yet. You can complete it as we go:

```
payment_processor
│
├── api
│   ├── __init__.py
│   └── views.py
├── migrations
│   ├── __init__.py
│   └── 0001_initial.py
├── models
│   ├── __init__.py
│   └── payment_methods.py
├── templates
│   └── forms
├── __init__.py
├── payment_processors.py
└── views.py
```

In `payment_processors.py` you will create your Payment Processor class. You should inherit
the PaymentProcessorBase class and a mixin class based on what type of your Payment Processor will be.
For more info, you should read the [payment processor resource definition](../resources.md#payment-processor).

We are going to "partially implement" a `triggered` Payment Processor.
That means the Transactions (payments) will be triggered from within Silver, and their status will
be mirrored to Silver either by polling or by webhooks if your payment processor service provides them.

```python
# payment_processors.py

import payment_processor_sdk

from silver.payment_processors import PaymentProcessorBase
from silver.payment_processors.mixins import TriggeredProcessorMixin

class TriggeredPaymentProcessor(PaymentProcessorBase, TriggeredProcessorMixin):
    template_slug = 'payment_processor_triggered'
```

There's not much in there at the moment so we'll try to add a way of creating an external (real)
transaction. We can do that by implementing the `execute_transaction` method.

```python
# payment_processors.py
# ...

class TriggeredPaymentProcessor(PaymentProcessorBase, TriggeredProcessorMixin):
    template_slug = 'payment_processor_triggered'

    def execute_transaction(self, transaction):
        """
            :param transaction: A Silver Transaction object in pending state, that hasn't been
            executed before.

            Creates a real, external transaction based on the given Silver transaction.

            Warning: You should never call this method directly! Use the `process_transaction`
                     method instead, which will call this method.
                     However, if you need to call it directly, make sure the transaction hasn't been
                     executed before.

            :return: True on success, False on failure.
        """

        # The following code is purely educational. Your code will probably look a lot different.
        # Start by creating your external transaction. You usually want to specify as many details
        # about the transaction as possible.
        transaction_result = payment_processor_sdk.create_transaction({
            'amount': transaction.amount,
            'currency': transaction.currency,
            'reference': str(transaction.uuid),
            # 'token': transaction.payment_method.token -- We'll discuss about this later.
        })

        # Most payment processors don't necessarily execute (authorize, submit for settlement...) the
        # transaction on their own, when creating the transaction. Let's do that:
        transaction_result = payment_processor_sdk.execute(transaction_result.id)

        # Update the Silver transaction to reflect the external's transaction new status
        self._update_transaction_status(transaction, transaction_result)

    def _update_transaction_status(self, transaction, transaction_result):
        """
            :param transaction: A silver transaction.
            :param transaction_response: A response object from the payment processor SDK.
            This method is not required by silver.
        """

        # You can do an additional check to make sure the two objects correlate:
        if not str(transaction.uuid) == transaction_result.reference:
            raise ValueError("The transaction and transaction_response don't match.")

        # First we update the Silver transaction's external reference and status
        transaction.external_reference = transaction_result.id
        status = transaction_result.status

        transaction.data.update({
            'status': status,
            'id': transaction_result.id
        })

        # Then we transition the Silver transaction to a new state if needed:
        if status == 'settled':
            transaction.settle()
        elif status == 'failed':
            transaction.fail()
        elif status == 'canceled':  # sometimes called voided
            transaction.cancel()
        elif status == 'refunded':
            transaction.refund()

        transaction.save()
```

You can specify codes and reason messages for the sad path transitions (fail, cancel, refund).
Silver has some predefined codes to which, if you wish, you can convert the codes provided by the SDK.

```python
from silver.models.transactions.codes import FAIL_CODES, CANCEL_CODES, REFUND_CODES, DEFAULT_FAIL_CODE

def _convert_to_silver_code(sdk_code):
    sdk_to_silver_codes = {}
    return sdk_to_silver_codes.get(sdk_code, DEFAULT_FAIL_CODE)

def _update_transaction_status(self, transaction, transaction_result):
    # ...
    fail_code = _convert_to_silver_code(transaction_result.error_code)
    transaction.fail(fail_code=fail_code, fail_reason=transaction_result.fail_reason)

    # Later if you want to send an email to your customer for example, you can use the generic messages
    # provided by silver
    print(FAIL_CODES[transaction.fail_code]['message'],
          FAIL_CODES[transaction.fail_code].get('solve_message', 'Contact our support'))
```

## Payment methods

You can implement a Payment Method class if you want to add specific payment method logic:
```python
# payment_processors.py
# ...
from .models.payment_methods import CustomPaymentMethod

class TriggeredPaymentProcessor(PaymentProcessorBase, TriggeredProcessorMixin):
    payment_method_class = CustomPaymentMethod
    #...
```

```python
# models/payment_methods.py
# ...
from silver.models import PaymentMethod

class CustomPaymentMethod(PaymentMethod):
    class Meta:
        proxy = True

    @property
    def token(self):
        return self.decrypt_data(self.data.get('token'))

    @token.setter
    def token(self, value):
        self.data['token'] = self.encrypt_data(value)  # self.encrypt_data is already implemented
```

You might have noticed that earlier when we implemented `execute_transaction`, we mentioned a token.
Most payment processors will provide you with a token because you are not supposed to handle the
customer's payment method info, so you will use the token to refer to the payment method instead.

The token is useful if the customer wants to save his payment method info for further or recurring
payments. Read about how you can obtain it in the [payment operation section](#the-payment-operation).
