#### 12 Dec. 2014
* Implement events for:
    * invoice/proforma state transitions
    * CRUD ops
    * subscription state transitions
* For auth use Basic Auth
* Check http://chibisov.github.io/drf-extensions/docs/#caching for the caching part

#### 12 Nov. 2014
* a `Provider` provides a `Plan`. So the `Plan` entity should link to the `Provider` entity
* `Plan` and `Metered Feature` are immutable
* `Offer` entity should be discussed a little bit more if it stays in this app or it should be done in the business logic
* `Product Code` should be a self contained entity and others should link to it.

#### 06 Nov. 2014

* What happens to the `Subscriptions` that are tied to a `Plan` that gets disabled? Should they automatically get canceled?

#### 30 Oct. 2014

* `Offer` resource which lists the plans available to a customer. If there is no offer for customer, than it can be subscribed to any _public plan_.
* The invoice series is per `Provider`.
* When to issue an invoice: when billing period ends, at the end of trial/at the beginning of subscription, when subscriptions is transitioned from cancel to end
* Consolidated billing by default. It should be per subscription. We also need a way to specify the billing consolidation (eg. per month, every two weeks etc.)
