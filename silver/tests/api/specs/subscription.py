from collections import OrderedDict

from silver.tests.api.specs.plan import spec_plan
from silver.tests.api.utils.path import absolute_url


def spec_subscription(subscription, detail=False):
    return OrderedDict([
        ("id", subscription.id),
        ("url", absolute_url("/customers/{customer_id}/subscriptions/{subscription_id}/".format(
            customer_id=subscription.customer.id,
            subscription_id=subscription.id
        ))),
        ("plan", (spec_plan(subscription.plan) if detail else
                  absolute_url("/plans/{plan_id}/".format(plan_id=subscription.plan.id)))),
        ("customer", absolute_url("/customers/{customer_id}/".format(
            customer_id=subscription.customer.id
        ))),
        ("trial_end", str(subscription.trial_end) if subscription.trial_end else None),
        ("start_date", str(subscription.start_date) if subscription.start_date else None),
        ("cancel_date", str(subscription.cancel_date) if subscription.cancel_date else None),
        ("ended_at", str(subscription.ended_at) if subscription.ended_at else None),
        ("state", subscription.state),
        ("reference", subscription.reference),
        ("updateable_buckets", subscription.updateable_buckets()),
        ("meta", subscription.meta),
        ("description", subscription.description)
    ])
