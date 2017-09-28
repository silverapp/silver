# Changelog

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
- The PDFs for Invoices and Proformas are now generated asynchronously using Celery tasks. Redis is required for locking. **(BREAKING)**
- PDFs now have their own model, therefore a migration has been created, which unfortunately fails to migrate the file url. **(BREAKING)**
A way to fix this would be to regenerate and re-upload the PDFs. Another way that should work would be to set the PDF.pdf_file.name value from the old Invoice.pdf_file.name.

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
