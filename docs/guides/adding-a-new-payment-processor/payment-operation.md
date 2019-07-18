---
title:  Part 2 - The payment operation
description: This section tries to explain how the customer's payment operation usually goes like.
linktitle: Part 2 - The payment operation
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

For this purpose, the following steps are described:

1. The customer usually clicks a Pay button somewhere in a different application, which will trigger a
[create request on the Silver's `/transactions` endpoint](../payments/transactions.md#create-a-transaction)

2. The transaction is created, and the response payload contains a field called `pay_url`, which
is a Silver URL that points to a view that will act as a payment page, which most likely you'll also
have to implement because of the differences between the payment processors.  
The `pay_url` expires after some time, based on the `SILVER_PAYMENT_TOKEN_EXPIRATION` setting and it
contains a different access token (JWT) every time it is generated. Therefore it is better to obtain
it right before the payer is about to access it. It cannot be accessed without the required access
token.  
You can read more about the payment page [here](#the-payment-page)

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
[the implementation example below](#handling-the-transaction-response-from-the-payment-processor).  

5. From there the client can be redirected to a final `redirect_url` or have a Silver template rendered
stating the state of the transaction.


## Handling the transaction response from the payment processor.

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


## The payment page
There's 3 things you usually want to implement / change for the payment page: The
[transaction form class](#the-transaction-form-class),
the [transaction form / payment page template](#the-transaction-form-template) and the
[transaction view class](#the-transaction-view-class).


### The transaction form class

The form class is only needed if the external payment processor service requires a form submission of
some sort.

You may specify it by using the `form_class` attribute of the PaymentProcessor class. It will be
rendered by default in the payment page, but you will probably be required to customize the
[form template](#the-transaction-form-/-payment-page-template) anyway.

You can override the PaymentProcessor's `get_form` method if you need more maneuverability.


### The transaction form template

The transaction form template represents (by default) the entire payment page template. If you want
to structure your templates differently, you can override the PaymentProcessor's `get_template` method.

By default it will be selected from one of the following paths:

- `templates/forms/{template_slug}/{provider_slug}_transaction_form.html`
- `templates/forms/{template_slug}/transaction_form.html`
- `templates/forms/transaction_form.html`

Where:

`template_slug` is an attribute of the PaymentProcessor class.

`provider_slug` is equal to `slugify(provider.company or provider.name)`, so if
`provider.company = "Some company"`, `provider_slug` will be equal to `some-company`.

``` python
# payment_processors.py
# ...

class TriggeredPaymentProcessor(PaymentProcessorBase, TriggeredProcessorMixin):
    template_slug = 'triggered_payment_processor'
```

You can override the context of the template by using a
[custom `transaction_view_class`](#the-transaction-view-class). The default context will contain data
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


### The transaction view class

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

At this point, you should have all the functioning pieces and if you are lucky they should fit together.

Now it's time to start writing some tests.
