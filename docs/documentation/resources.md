---
title: Silver resources
description: Here is a list of all the resources available in Silver, as well as how they interact. All their parameters and methods are described in detail, for a better understanding of their functionality.
---
Resources:

1. [Plan](#plan)
2. [Metered feature](#metered-feature)
3. [Customer](#customer)
4. [Provider](#provider)
5. [Subscription](#subscription)
6. [Billing Document](#billing-document)
7. [Invoice](#invoice)
8. [Proforma](#proforma)
9. [Document entry](#document-entry)
10. [Coupon](#coupon)
11. [Discount](#discount)
12. [Offer](#offer)
13. [Add-on feature](#add-on-feature)
14. [Payment Method](#payment-method)
15. [Payment Processor](#payment-processor)
16. [Processor Manager](#payment-manager)
17. [Customer Details](#customer-details)
18. [Transaction](#transaction)

---

#### Plan:
* `(string) name`: Display name of the plan.
* `(string) interval = 'month'`: One of `day`, `week`, `month` or `year`. The frequency with which a subscription should be billed.
* `(positive int) interval_count = 1`: The number of intervals (specified in the interval property) between each subscription billing. For example, `interval=month` and `interval_count=3` bills every 3 months.
* `(positive decimal) amount = 0.0000`: The amount in the specified currency to be charged on the interval specified.
* `(string) currency`: Currency in which subscription will be charged.
* `(positive int) trial_period_days = NULL`: Number of trial period days granted when subscribing a customer to this plan. `NULL` if the plan has no trial period.
* `(MeteredFeature list) metered_features = NULL`: A list of plan's [metered features](#metered-feature).
* `(positive int) generate_after = 0`: Number of seconds to wait after current billing cycle ends before generating the invoice. This can be used to allow systems to finish updating feature counters.
* `(boolean) enabled = True`: Whether to accept subscriptions
* `(boolean) private = False`: This is a private plan (eg. one made specifically for one customer).
* `(ProductCode) product_code`: The product code for this plan.
* `(Provider) provider`: The provider of the plan.

#### Metered feature:
It's a feature of which a number of units can be added during billing cycle. At the end of the billing cycle, it's calculated by multiplying `price_per_unit` and the number of reported units. An example of metered feature is `bandwidth`. A metered feature has the following structure.
* `(string) name`: The feature name.
* `(string) unit`: The metered feature's unit.
* `(positive decimal) price_per_unit = 0.0000`: The price per unit.
* `(positive decimal) included_units = 0.0000`: The number of included units per plan interval.
* `(positive decimal) included_units_during_trial = NULL`: The number of included units during the trial period. If this field is empty, it is considered that all the consumed metered features are free.
* `(ProductCode) product_code`: The product code for this features.

#### Customer:
* `(string) customer_reference`: It's a reference to be passed between silver and clients. It usually points to an account ID.
* `(positive int) payment_due_days`: Due days for generated invoices.
* `(hash) billing_details`: An hash consisting of billing information. None are mandatory and all will show up on the invoice.
  * `(string) name`: The name to be used for billing purposes.
  * `(string) company`: Company to issue invoices to.
  * `(string) email`: Customer email
  * `(string) address_1`:
  * `(string) address_2`:
  * `(string) country`:
  * `(string) city`:
  * `(string) zip_code`:
  * `(string) extra`: Extra information to display on the invoice (markdown formatted).
* `(string) sales_tax_number = NULL`: Sales tax number (eg. U1234567 or other valid VAT number formats)
* `(positive decimal) sales_tax_percent = NULL`: Whenever to add sales tax. If null, it won't show up on the invoice.
* `(string) sales_tax_name = NULL`: Sales tax name (eg. 'sales tax' or 'VAT').
* `(boolean) consolidated_billing = False`: It indicates if the customer uses consolidated billing.

#### Provider:
* `(string) name`: The name of the provider.
* `(string) company`: The company issuing the invoice.
* `(string) flow = 'proforma'`: The flow that will be used for generating invoices. Can be one of the following:
    * `'proforma'`: First generate a proforma and then automatically generate the corresponding invoice when the proforma is paid.
    * `'invoice'`: Generate invoices directly and ignore the existence of proformas.
* `(string) invoice_series = NULL`: The series that will be used on the provider's invoices.
* `(positive int) invoice_starting_number`: The start value for the auto-generated invoice number.
* `(string) proforma_series = NULL`: The series that will be used on the provider's proformas.
* `(positive int) proforma_starting_number`: The start value for the auto-generated invoice number.
* `(string) default_document_state`: The default state of the auto-generated documents.
* `(string) email = NULL`: The e-mail address of the provider.
* `(string) address_1`:
* `(string) address_2 = NULL`:
* `(string) country = NULL`:
* `(string) city`:
* `(string) state = NULL`:
* `(string) zip_code`:
* `(string) extra = NULL`: Extra information to display on the invoice (markdown formatted).

#### Subscription:
* `(plan) plan`: The plan the customer is subscribed to.
* `(string) description = NULL`: The subscription's description.
* `(string) reference = NULL`: The subscription's reference in an external system.
* `(customer) customer`: Customer who is subscribed to the plan.
* `(date) start_date`: The starting date for the subscription
* `(date) trial_end = NULL`: The date at which the trial ends. If set, overrides the computed trial end date from the plan.
* `(date) cancel_date = NULL`: The cancel date of the subscription.
* `(date) ended_at = NULL`: If the subscription has ended (either because it was canceled or because the customer was switched to a subscription to a new plan), the date the subscription ended
* `(string) state = 'active'`: The state the subscription is in. Can be one of the following:
    * `inactive`: Subscriptions in this state need to be activated for example by a human review. In this state they will not generate any invoices nor accept any updates to metered features. If not set, the `trial_end` date is set by switching the subscription to `active` state. Also, the `start_date` must be specified when switching from `inactive` to `active`.
    * `active`: Subscriptions in this state generate invoices as normal.
    * `canceled`: The subscription is canceled an has to be billed the next time that the `generate_docs` command runs.
    * `canceled`: The subscription will be billed and ended only at the beginning of the new billing cycle. Note that usually the `generated_docs` command runs regularly (e.g.: hourly), not just at billing cycles start.
    * `ended`: The subscription is ended due to upgrade, cancellation or being unpaid.
* `(BillingLog list) billing_log_entries`: Contains the billing history (dates) of a subscription.

#### Billing document:
This is fully inherited by [invoice](#invoice) and [proforma](#proforma).

* `(integer) number`: The number of the billing document. It will be generated automatically.
* `(date) due_date = NULL`: The due date of the billing document.
* `(date) issued_date = NULL`: The billing document's issue date.
* `(date) paid_date = NULL`: The billing document's paid date.
* `(date) cancel_date = NULL`: The billing document's canceled date.
* `(Customer) customer`: The billing document's customer.
* `(Provider) provider`: The billing document's provider.
* `(DocumentEntry list) entries`: billing [document entries](#document-entry).
* `(positive decimal) sales_tax_percent = NULL`: Whenever to add sales tax. If null, it won't show up on the billing document.
* `(string) sales_tax_name = NULL`: Sales tax name (eg. 'sales tax' or 'VAT').
* `(string) currency`: Currency in which the billing document is issued.
* `(boolean) past_due = False`: Indicates if the billing document is past due.
* `(string) state = 'draft'`: The state the billing document is in. Can be one of the following:
    * `draft`: This is, by default, the billing document initial state. In this state, the billing document can be modified.
    * `issued`: The billing document is issued. In this state, the billing document cannot be modified anymore and it's waiting to be either paid or canceled. When switching to this state, the customer's `billing_details` are copied into `billing_details` and `issued_date` is set.
    * `paid`: The billing document has been paid.
    * `canceled`: The billing document has been canceled.

#### Invoice:
An invoice is a type of [billing document](#billing-document) and it inherits all the fields found in a billing document.
Additional fields, specific to an invoice:
* `(Proforma) proforma = NULL`: The proforma to whom the invoice is associated.

#### Proforma:
A proforma is a type of [billing document](#billing-document) and it inherits all the fields found in a billing document.
Additional fields, specific to a proforma:
* `(Invoice) invoice = NULL`: The invoice to whom the proforma is associated.

#### Document entry:
* `(string) description`: The billing document's entry description.
* `(string) unit`: The billing document's entry unit.
* `(positive decimal) quantity = 1.0000`: The billing document's entry quantity.
* `(positive decimal) unit_price`: The price per unit.
* `(ProductCode) product_code = NULL`: An eventual product code.
* `(date) start_date = NULL`: If the billing document entry applies to an eventual date range, like a metered feature bucket, the start date of that range
* `(date) end_date = NULL`: The same as `start_date` but for the ranges end date.
* `(boolean) prorated = False`: This entry is a result of a proration, like for example the first half-month.
* `(Invoice) invoice = NULL`: The invoice to whom it belongs.
* `(Proforma) proforma = NULL`: The proforma to whom it belongs.

---

#### Payment Method:
* `payment_processor (PaymentProcessorField)`: The payment processor of the payment method.
* `customer (FK to Customer)`: The customer that owns the payment method.
* `added_at (Datetime, autoadd=now)`: Datetime when the payment method was added.
* `verified_at (Datetime, null, autoadd)`: Datetime when the payment was verified.
* `data (JSON, null)`: Can store various information. E.g. token that can be used to link the payment method to an external resource / service.
* `state (String, choices=`[PaymentMethod.State](#paymentmethodstate)`)`: The state of the payment method.

###### PaymentMethod.State
```
   uninitialized ---> unverified
             \         /
              \       /
               V     V
               enabled <----> disabled
                    \         /
                     \       /
                      V     V
                      removed
```

---


#### Payment Processor:
> The base class of a payment processor. Specific payment processors will have to extend this class.
_This is not a Django Model_


* `type (Class constant String, choices=('manual', subclasses-only:['automatic', 'triggered']))`  
   _**manual** - The transactions are initiated by a Silver client. Their status is also verified/managed by a Silver client (e.g admin)._  
   _**triggered** - The transactions are initiated by a Silver client or triggered by a mechanism within Silver. Their status is verified/managed by the Payment Processor._  
   _**automatic** - The transactions are initiated by the real Payment Processor services. Their status are managed by the real Payment Processor services, but are synced in Silver by the Payment Processor class._  

###### Methods:
* `charge_payment(payment, payment_method=None)`  
  _This method will be called whenever the processor should attempt to process the payment using the given payment method._  

   _**Returns** a boolean that describes if the charge attempt was succesful or not._  

* `refund_payment(payment, payment_method=None)`  

* `void_payment(payment, payment_method=None)`  

* `manage_payment(payment)`  

---


#### Processor Manager:
> Holds a list of all the available [Payment Processors](#payment-processor).

* `processors (Payment Processor list)` - stores the available payment processors.

###### Methods
* `register(payment_processor, setup_data={})`  
  _Adds the `payment_processor` to the `processors` list and also sets the `status` of that specific Payment Processor Class._  
  _The Payment Processors specified in the Django settings variable `PAYMENT_PROCESSORS` are automatically registered._
* `get(payment_processor_name)`  
  _Returns an instance of the payment processor class or raises a `PaymentProcessorManager.DoesNotExist` exception if the payment processor with that name is not found._  
* `all()`  
  _Returns a list of all the registered Payment Processors._  
* `get_choices()`  
  _Returns choices for the PaymentProcessorField_   

---


#### Transaction:
> It's the relation between a Document and a Payment Method. It holds the state of the payment processing and it can be used to initiate the payment processing.

* `state (String choices=`[Transaction.State](#transactionstate)`)`: The state of the transaction.
* `payment_method (ForeignKey to `[Payment Method](#payment-method)`)`
* `invoice (ForeignKey to `[Invoice](#invoice)`)`
* `proforma (ForeignKey to `[Invoice](#proforma)`)`
* `amount (Decimal)`: The amount to be charged from the customer. Must be equal (or lower - not yet implemented) to the amount on the document.
* `currency (String choices=`pycountry.currencies`, default='USD'): The currency used for billing.
* `currency_rate_date (Date, null)`: The date of the currency rate.
* `uuid (UUID, default=uuid.uuid4)`
* `valid_until (DateTime, null)`
* `last_access (DateTime, null)`
* `disabled (Bool, default=False)`

###### Transaction.State
```
             unpaid ---------------
            /  ^                  |
          /    |                  |
        /      |                  |
      V        V                  |
canceled <-- pending --> failed   |
               |                  |
               |                  |
               V                  |
               paid <--------------
```

Done
