---
title:  Adding a new payment processor
description: This guide will explain the steps of adding a new payment processor to Silver.
linktitle: Adding a new payment processor
categories: [silver]
keywords: [silver]
menu:
  docs:
    parent: "guides"
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

- Create your app
```bash
./manage.py startapp payment_processor
```

- Add it to your INSTALLED_APPS in your settings file
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

- Create your project
```bash
django_admin startproject payment_processor
```

- Install it by linking it inside your main project's environment, where Silver is also installed
```bash
workon silver_project  # Change to your main project's environment
cd payment_processor  # Go to your payment_processor's directory
pip install -e .  # Install your payment_processor development project as a linked dependecy
```

- Add the payment_processor to your INSTALLED_APPS in your silver_project's settings file
```python
INTERNAL_APPS = [
    'silver',
    'payment_processor',
    # ...
]
```


## Implementation

### Deciding how your Payment Processor will look

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
For more info, you should read the [payment processor resource definition]({{< ref "../resources.md#payment-processor" >}}).

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

### Payment methods

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
payments. Read about how you can obtain it in the [payment operation section]({{< ref "#the-payment-operation" >}}).

### The payment operation

This section tries to explain how the customer's payment operation usually goes like. For this purpose
the following steps are described:

1. The customer usually clicks a Pay button somewhere in a different application, which will trigger a
[create request on the Silver's `/transactions` endpoint]({{< ref "../payments/transactions.md#create-a-transaction" >}})

2. The transaction is created, and the response payload contains a field called `pay_url`, which
is a Silver URL that points to a view that will act as a payment page, which most likely you'll also
have to implement because of the differences between the payment processors.  
The `pay_url` expires after some time, based on the `SILVER_PAYMENT_TOKEN_EXPIRATION` setting and it
contains a different access token (JWT) every time it is generated. Therefore it is better to obtain
it right before the payer is about to access it. It cannot be accessed without the required access
token.  
You can read more about the payment page [here]({{< ref "#the-payment-page" >}})
3. The App redirects the customer to the `pay_url`. There the customer can enter its payment method
info and accept the transaction.  
Keep in mind the customer might choose to cancel the operation, enter wrong or expired payment method
data etc.. In some cases the customer might be redirected from the Silver payment page to the external
Payment Processor payment page.
4. Depending on the outcome of the operation, the customer may be redirected to the
`complete_payment_view` Silver view, which will call the `handle_transaction_response` method of our
`TriggeredPaymentProcessor` class.  
Sometimes the payment processor won't rely on the customer to access `the complete_payment_view` (since
it is not a guarantee it will happen) and will send a webhook containing info about the external
transaction.
The `handle_transaction_response` method is where we can update our
transaction reference and status. See
[the implementation example below]({{< ref "#handling-the-transaction-response-from-the-payment-processor" >}}).  
5. From there the client can be redirected to a final `redirect_url` or have a Silver template rendered
stating the state of the transaction.


#### Handling the transaction response from the payment processor.
```python
# payment_processors.py
# ...

class TriggeredPaymentProcessor(PaymentProcessorBase, TriggeredProcessorMixin):
    #...
    def handle_transaction_response(self, transaction, request):
        """
            :param transaction: A Silver Transaction object.
            :param request: A Django request object. It should contain POST (or GET) data about the
            transaction, which will be used to update the Silver Transaction.

            This method should update the transaction info (external reference, state ...) after the
            first HTTP response from the payment gateway.

            It will automatically be called by the `complete_payment_view`.

            If not needed, one can `pass` it or just `return`.
        """

        # For the sake of simplicity we'll reuse our previously added _update_transaction_status method
        self._update_transaction_status(transaction, request.POST.get('transaction_result'))

        # If the payment processor allows it and the customer requested to save the payment method,
        # a token can be provided in the request.POST data
        # You can update the payment method in the _update_transaction_status method if you wish,
        # or do it here
        transaction.payment_method.data['token'] = request.POST.get('token')
        # You'll be able to reuse the token for a later payment or recurring payments
```

As mentioned earlier in step 4, the payment processor might offer a different solution to obtaining the
transaction's "initial" information. In this case you can just pass the payment processor's webhook
request to this method or just `pass` inside the `handle_transaction_response` method and handle this
logic somewhere else. The implementation details are really up to you.


#### The payment page
There's 3 things you usually want to implement / change for the payment page: The
[transaction form class]({{< ref "##handling-the-transaction-response-from-the-payment-processor#the-transaction-form-class" >}}),
the [transaction form / payment page template]({{< ref "#the-transaction-form-template" >}}) and the
[transaction view class]({{< ref "#the-transaction-view-class" >}}).


##### The transaction form class
The form class is only needed if the external payment processor service requires a form submission of
some sort.

You may specify it by using the `form_class` attribute of the PaymentProcessor class. It will be
rendered by default in the payment page, but you will probably be required to customize the
[form template]({{< ref "#the-transaction-form-/-payment-page-template" >}}) anyway.

You can override the PaymentProcessor's `get_form` method if you need more maneuverability.


##### The transaction form template
The transaction form template represents (by default) the entire payment page template. If you want
to structure your templates differently, you can override the PaymentProcessor's `get_template` method.

By default it will be selected from one of the following paths:
- `templates/forms/{template_slug}/{provider_slug}_transaction_form.html`
- `templates/forms/{template_slug}/transaction_form.html`
- `templates/forms/transaction_form.html`
Where:
- `template_slug` is an attribute of the PaymentProcessor class  
- `provider_slug` is equal to `slugify(provider.company or provider.name)`, so if
`provider.company = "Some company"`, `provider_slug` will be equal to `some-company`

```python
# payment_processors.py
# ...

class TriggeredPaymentProcessor(PaymentProcessorBase, TriggeredProcessorMixin):
    template_slug = 'triggered_payment_processor'
```

You can override the context of the template by using a
[custom `transaction_view_class`]({{< ref "#the-transaction-view-class" >}}). The default context will contain data
such as the `transaction`, `payment_method`, `customer`, `form`...

Now on to actually writing your transaction_form template. A good starting point would be the following
example:

```html
# templates/forms/triggered_payment_processor/transaction_form.html

{% extends 'forms/transaction_form.html' %}

{% block form %}
    {{ block.super }}
{% endblock %}

{% block transaction %}
    {{ block.super }}
{% endblock %}
```

You might have to insert javascript from your payment processor, apply some custom styling, or point
the form to a service of your payment's processor. That's all up to you.

Here's a couple of real world examples that might shed some light if you are confused:
1. [PayU transaction form template](https://github.com/silverapp/silver-payu/blob/master/silver_payu/templates/payu/transaction_form.html)  
   [Here](https://github.com/silverapp/silver-payu/blob/master/silver_payu/templates/payu/payu_lu_form.html)
    is one of the form templates that are used inside. You can see the form action has been changed to point to
    the payment processor's endpoint.
2. [Braintree transaction form template](https://github.com/silverapp/silver-braintree/blob/master/silver_braintree/templates/forms/braintree/transaction_form.html)  
    You can see some custom javascript being inserted in there. Also, notice that a Silver form is not used.
    Instead, one is loaded from the payment processor via a script.


##### The transaction view class
You need to specify a transaction view class inside your PaymentProcessor's class. It can be the default
`GenericTransactionView` class or a custom one.

```python
# payment_processors.py
# ...

class TriggeredPaymentProcessor(PaymentProcessorBase, TriggeredProcessorMixin):
    transaction_view_class = CustomTransactionView
    # ...
```

```python
# views.py
#...
from silver.payment_processors import get_instance as get_payment_processor
from silver.payment_processors.views import GenericTransactionView


class CustomTransactionView(GenericTransactionView):
    def get_context_data(self):
        # An example of changing the form template's context

        context_data = super(CustomTransactionView, self).get_context_data()
        payment_processor = get_payment_processor(self.transaction.payment_processor)

        context_data['allowed_currencies'] = payment_processor.allowed_currencies

        return context_data

    def get(self, request):
        # Do something special here

        return HttpResponse(self.render_template())
```


### Wrapping it all up
At this point, you should have all the functioning pieces and if you are lucky they should fit together.

Now it's time to start writing some tests.


#### Testing
Depending on your implementation, you might want to write some unit tests for your
`TriggeredPaymentProcessor` class, your `TriggeredPaymentMethod` model, your forms, and then some
integration tests for your views. You should at least test every method that you've written so far.

A general advice is to remember to not just test the happy paths, but also the sad paths.

Mocking your `payment_processor_sdk` may or may not be a good idea. These usually don't change their API
very often, and when they do you're most likely going to have to rewrite your PaymentProcessor
implementation anyway. The good part about mocking is you won't rely on the payment processor to offer
you a sandbox account for testing or ensure that their testing services are always working.

For peace of mind, you might want to write some in-browser integration tests, using a tool like Selenium.

Ultimately you'll have to test the whole thing yourself using a production account and a real payment
method, at least once. Some errors will not show up in the sandbox environment offered by your payment
processor. Read the documentation of your `payment_processor_sdk` carefully, and deliberately search for
these potential errors and exceptions. Most of the time the "getting started" guides only tackle the
happy path, leaving out most of the error handling.

If you stumbled upon problems that were not tackled in this guide, consider improving it by contributing
your experience.
