# Changelog

## Unrealeased changes
_Nothing yet_

## 0.7 (2019-01-07)
Some of these changes that were considered to be possibly breaking were marked with **(WARNING)**.
- Added Python 3.5 and 3.6 compatibility while maintaining Python 2.7 compatibility for now. **(WARNING)**
- Fixed not being able to later settle a transaction related to a manually paid document.
- Removed pytz dependency.
- Bumped cryptography version.

## 0.6.2 (2018-08-10)
- Fixed a bug where a canceled subscription would not be billed if the plan was billed up to a date
later than the cancel date.
- Fixed Transaction return_url being quoted because of a new version of furl, which has also been
pinned to known working versions.

## 0.6.1 (2018-05-08)
Some of these changes that were considered to be possibly breaking were marked with **(WARNING)**.
- Subscription's meta field now defaults to an empty dict. **(WARNING)**
- Added cancel_date to SubscriptionSerializer.

## 0.6 (2018-04-25)
Some of these changes that were considered to be possibly breaking were marked with **(WARNING)**.
- Dropped Django 1.8 support, meaning only Django 1.11 is currently supported. **(WARNING)**
- PDF generate method will no longer mark the `PDF` object as clean if the file is not saved
  (through the `upload` method) **(WARNING)**
- Fixed a potential bug, involving the same `PDF` object and multiple threads, where the `PDF`
  `mark_as_dirty` method would fail to work properly.

## 0.5.5 (2018-03-30)
- Make sure to use the plan currency when generating documents.

## 0.5.4 (2018-02-14)
- Also store plan and metered feature amounts separately in Billing Logs.

## 0.5.3 (2018-01-09)
- Increase phone number limits to 32, since there are a lot of phone formats.

## 0.5.2 (2017-12-28)
- Small admin interface improvements for payment methods and transactions
- Solved archived customer bug. In some cases, the `name` attribute of an
  archived customer could be pass to the BillingEntity contructor,
  resulting in a 500 error (since BillingEntity) doesn't have a `name` argument.
- Fix DocumentAutocomplete bug. DocumentAutocomplete would fail if a `-` is
  pressent in query.

## 0.5.1 (2017-12-04)
- Pin html5lib to 1.0b8 since this is a stable version working with xhtml2pdf

## 0.5 (2017-12-04)
Some of these changes are considered to be breaking and were marked with **(BREAKING)**
- Implementations of payment processors don't have to call the `process` method on the transaction
anymore. A new method called `process_transaction` has been added for actionable PaymentProcessors
which tries to call the transaction `process` method. This has been done to avoid a case of duplicate
transactions. **(BREAKING)**

## 0.4.4 (2017-11-20)
- Fixed some tests that were behaving differently when run inside a parent application.
- Use a custom working xhtml2pdf version for pdf generation
- Add `SILVER_SHOW_PDF_STORAGE_URL` option. If `False`, `pdf_url` for document
  endpoints, will display an url to a view that will redirect to the actual
  document url. This is a small optimization in case you are using external
  document storages (like S3 or Google Storage), because it can take up to 1-2
  seconds for them to generate secrets token for secured urls. By default it is
  `True` which mean that the old behaviour is still up.

## 0.4.3 (2017-11-16)
- Reduce query numbers for some API endpoints (`/plans`,
  `/customers/subscriptions`) and admin

## 0.4.2 (2017-11-16)
- Remove django-xhtml2pdf
- Adapt pdf generation for Django 1.8 and 1.11

## 0.4.1 (2017-11-15)
Add deleted customer and id filters on document list endpoint.

## 0.4 (2017-11-15)
Some of these changes are considered to be breaking and were marked with **(BREAKING)**
- Invoice and Proforma are now Proxy models of the BillingDocumentBase model, which is no longer
abstract. This allows for an easier aggregation in the /documents API endpoint. Both models should
still be usable as before and BillingDocumentBase instances should automatically be assigned
their concrete class, depending on their `kind` field. **(BREAKING)**

## 0.3.13 (2017-11-08)
- Add `_total` and `_total_in_transaction_currency` to document base.

## 0.3.12 (2017-11-08)
- Optimize document view queries (30% speed improvement).

## 0.3.11 (2017-11-08)
- Optimize document view queries (37% speed improvement).

## 0.3.10 (2017-11-01)
- Fixed subscription end of billing cycle cancel date.
- Added development requirements via `setup.py`.

## 0.3.9 (2017-11-01)
- Fixed updateable_buckets end_date not being the bucket_end_date for a canceled subscription.

## 0.3.8 (2017-11-01)
Some of these changes that were considered to be possibly breaking were marked with **(WARNING)**.
- Fixed not being able to create Metered Feature Units Logs through the API if the subscription
is canceled but not past the cancel_date.
- Updateable buckets past the subscription cancel date are no longer valid. **(WARNING)**

## 0.3.7 (2017-10-27)
Some of these changes that were considered to be possibly breaking were marked with **(WARNING)**.
- Old PDFs are no longer deleted on PDF regeneration. **(WARNING)**

## 0.3.6 (2017-10-17)
- Fixed execute_transactions task name.

## 0.3.5 (2017-10-02)
- Added some missing fields to Provider and Plan in admin.

## 0.3.4 (2017-10-02)
- Fixed execute_transactions task name.

## 0.3.3 (2017-10-02)
- Added 'cycle_billing_duration' field to the Provider and Plan model, with both fields being optional,
and the Plan one having priority over the Provider one. This field can be used to ensure that the billing
date doesn't pass a certain date. Billing documents can still be generated after that day during the billing
cycle, but their billing date will appear to be the end of the cycle billing duration.
```
V-----------billing cycle--------------V
[===============|=================|====]
^-cycle billing-^                 ^
|---duration----|            billing date
                ^
    last possible billing date

Generating after the <last possible billing date> during this <billing cycle>
is possible but will use the <last possible billing date> as the <billing date>.
```
- Added a `created_at` field to BillingLog.
- Display `plan_billed_up_to`, `metered_features_billed_up_to` and `created_at` BillingLog fields in admin.
- Fixed `generate_after` field not being properly considered when generating documents.
- Fixed being able to generate documents for a canceled subscription during the cancel_date day.
The right behavior is generating the documents after the cancel_date.

## 0.3.2 (2017-09-28)
*Version 0.3.0 and 0.3.1 were published with errors.*
Some of these changes that were considered to be possibly breaking were marked with **(WARNING)**.
- Celery and Redis are no longer a requirement, as the django commands and celery tasks
that are supposed to be run periodically now have equivalents in both versions.
Using celery tasks is still the recommended way to go.
- Refactored a fair part of the logic responsible for automatic billing documents generation.
This change might affect the way in which trial periods are handled, but it was necessary as the
old code was really hard to maintain and even understand in some places.
To allow configuring the billing cycles, the following fields were added to the Provider and Plan models,
with the Plan ones being optional and having priority over the Provider ones: **(WARNING)**
  - `generate_documents_on_trial_end`
  - `separate_cycles_during_trial`
  - `prebill_plan`
- BillingLog now has two additional date fields (`plan_billed_up_to` and `metered_features_billed_up_to`)
that better describe what was already billed. An attempt to populate the existing Billing Logs with these
fields was made through a migration, but it's possible that certain billing cycles involving trial periods
might be off. Make sure to double check the next wave of automatically generated documents. **(WARNING)**
- A clear example of behavior change is that generating a canceled subscription's invoice will no longer wait
for the next months invoices to be generated even if the customer has consolidated billing.
- Removed versioneer. Going back to good old manual versioning.

## 0.2.16 (2017-08-23)
*Version 0.2.15 was published with errors.*
- Added a total field to BillingLog, to store the amount a subscription has been billed with.
- Fixed API pagination headers.

## 0.2.12 (2017-07-24)
*Versions 0.2.9 to 0.2.11 were published with errors.*
- Silver now supports both Django 1.8 and 1.11.
- Added an Admin action that allows marking PDFs for generation.
- Transactions and Payment Methods are now ordered by default descendingly by id.

## 0.2.8 (2017-07-17)
Some of these changes are considered to be breaking and were marked with **(BREAKING)**
- The PDFs for Invoices and Proformas are now generated asynchronously using Celery tasks. Redis is 
required for locking. **(BREAKING)**
- PDFs now have their own model, therefore a migration has been created, which unfortunately fails 
to migrate the file url. **(BREAKING)**
A way to fix this would be to regenerate and re-upload the PDFs. Another way that should work would 
be to set the PDF.pdf_file.name value from the old Invoice.pdf_file.name.

## 0.2.7 (2017-02-08)
- Added a setting that allows automatically creating transaction when a payment method is verified.
- Added an actions API endpoint for transactions, that currently allows canceling a transaction.
- Round all totals with 2 decimals.
- Properly validate the transaction amount against the document's total_in_transaction_currency field.

## 0.2.6 (2017-02-07)
- Admin UI usability improvements
- Fix the sum of the entries of an invoice not always corresponding to the invoice's total because of rounding.

## 0.2.5 (2017-02-06)
- Only use active and verified payment methods to execute transactions.

## 0.2.4 (2017-02-06)
- Some fixes regarding the automatic transaction creation logic.

## 0.2.3 (2017-02-06)
- Removed default value for document's transaction_currency. **(WARNING)**

## 0.2.2 (2017-02-03)
Some of these changes that were considered to be possibly breaking were marked with **(WARNING)**.
- Added total_in_transaction_currency field to Invoice and Proforma serializers.
- Created template blocks for Issuer and Customer in transaction_form.html template. **(WARNING)**

## 0.2.1 (2017-02-03)
Some of these changes that were considered to be possibly breaking were marked with **(WARNING)**.
- Admin UI fixes and usability improvements.
- Billing documents transaction_xe_date will have the same value as issue_date by default. **(WARNING)**
- Other currency related fixes.
- Added valid_until and display_info fields to PaymentMethod model.
- Added total_in_transaction_currency field to DocumentSerializer.
- Added transaction_currency field to the Document model.

## 0.2 (2017-02-02)
Some of these changes were part of 0.1.5b (2016-11-18)
Some of these changes that were considered to be possibly breaking were marked with **(WARNING)**.
- Added payments models, logic and API endpoints.
- Split models into separate files. **(WARNING)**
- Added a readonly documents API endpoint, exposing both Invoices and Proformas.
- Split customer name field into two fields: first_name and last_name. **(WARNING)**
- Fixed pycountry dependency.
- Added docker build support.
- Added versioneer for version management.
- Other small fixes and improvements

## 0.1.4 (2016-08-17)
- Adapt silver to pep8 standard #328
- Replace django-international with pycontry #329
- Minor issue related to subscription #320
- Api filtering by multiple references #323
- generate_docs accept string and datetime #318
- Catch untreated exception when paying related documents #315
- Avoid documents transition double signal triggering.
- Fix draft documents number #312
- Removed pinned versions from requirements.txt #310
- Fix some unicode issues #304
- Added subscription state change logs

## 0.1.3
- Upgraded to Django 1.8.9

## 0.1.2
- Remove debug traces

## 0.1.1
- Fix setup.py

## 0.1.0
- Initial release
