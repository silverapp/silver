---
title:  Part 3 - Testing
linktitle: Part 3
description: The last part of this tutorial gives you some keen insights about what tests you should write for your newly created payment processor.
keywords: [silver]
menu:
  global:
    parent: "adding-a-new-payment-processor"
---

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
