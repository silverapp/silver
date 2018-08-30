---
title: Subscriptions in Silver
description: An overview of what is a Subscription in Silver, how to list a customer's subscriptions, as well as the basic operations it supports, like create, activate, cancel and more.
---
For resource definition check out [Resources](Resources#subscription) page.

1. [List a customer's subscriptions](#listing-a-customers-subscriptions)
2. [Creating a subscription](#creating-a-subscription)
3. [Retrieving a subscription](#retrieving-a-subscription)
4. [Activating a subscription](#activating-a-subscription)
5. [Canceling a subscription](#canceling-a-subscription)
6. [Reactivate a subscription](#reactivate-a-subscription)
7. [Update subscription metered feature](#update-subscription-metered-feature)
8. [Extend trial period (not implemented)](#extend-trial-period)

##### Listing a customer's subscriptions
By default this will list every Subscription related to a specific customer.
```
GET /customer/:id/subscriptions
```
Filters can be used for better results. The available filters are `plan`, `reference` and `state`.
```
GET /customer/<customer-id>/subscriptions?plan=Hydrogen&state=active
```
##### Creating a subscription
```
POST /customer/:id/subscriptions
{
    'plan': 'http://api.example.com/plans/1',
    'customer': 'http://api.example.com/customer/32',
    'trial_end_date': null,
    'start_date': '2014-10-18'
}
```
##### Retrieving a subscription
```
GET /customers/:customer_id/subscriptions/:subscription_id
```
Will return a subscription object and a list of plans `metered_features`.

##### Activating a subscription
When activating a subscription the following happens:
* the subscription `start_date` is set to the current date, if it isn't already set or given in the request;
* the subscription `trial_end_date` is computed from `start_date` plus the plan's `trail_period_days`, if it hasn't been already set or given in the request;
* the subscription `state` is transitioned to `active`.

Some validation checks must be done so that the `start_date` is older or equal to the `trial_end_date`. This transition is only available from the `inactive` state.

```
POST /customers/:customer_id/subscriptions/:subscription_id/activate/
{
    'start_date': '2014-10-18',
    'trial_end_date': '2014-11-3'
}
```

##### Canceling a subscription
When sending the POST request, a `when` parameter needs to be provided. It can take two values: `now` and `end_of_billing_cycle`.

When canceling a subscription `now`, a final invoice is issued and the subscription is transitioned to `ended` state.
When canceling a subscription at the `end_of_billing_cycle` the subscription is only transitioned to the `canceled` state. At the end of the billing cycle a final invoice will be issued and the subscription will be transitioned to the `ended` state.

```
POST /customers/:customer_id/subscriptions/:subscription_id/cancel/
{
    'when': 'now'
}
```

##### Reactivate a subscription
Subscriptions which are canceled, can be reactivated before the end of billing cycle. The request just transitions a subscription from `canceled` to `active`.
```
POST /customers/:customer_id/subscriptions/:subscription_id/reactivate/
```

##### Update subscription metered feature
Each Subscription has Metered Features Units Logs that correspond to the Plan's Metered Features.
A Units Log consists of multiple buckets representing billing cycles.

For example if we have a monthly plan, recurring every month and if the subscription `start_date` is '2014-10-8', the `trial_end_date` is '2014-10-23' and the `end_date` is '2014-12-28', then the buckets will look like this:
* 2014-10-08 -> 2014-10-23, marked as `trial`
* 2014-10-24 -> 2014-11-01
* 2014-11-01 -> 2014-11-30
* 2014-12-01 -> 2014-12-28


In order to perform an update the subscription must be active.
There are 3 parameters required in the request body: `count`, `update_type` and `date`.

The `count` parameter is the value to update the bucket with and it can be either positive or negative.

The `update_type` parameter can be absolute (meaning the new bucket value will be equal to the count value) or relative (meaning the count value will be added to the bucket value).

The bucket is determined using the `date` parameter.
The buckets can be updated until the time given by the bucket `end_date` + the plan's `generate_after` seconds is older than the time when the request is made.
After that, the buckets are frozen and cannot be updated anymore.

Requests that are invalid or late will return a HTTP 4XX status code response.
```
PATCH /customers/:customer_id/subscriptions/:subscription_id/metered-features/:metered_feature_product_code
{
        "count": 12345.0000,
        "date": "2015-02-20",
        "update_type": "absolute"
}
```
