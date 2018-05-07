from collections import OrderedDict
from decimal import Decimal

from silver.tests.api.specs.metered_feature import spec_metered_feature
from silver.tests.api.utils.path import absolute_url


def spec_plan(plan):
    return OrderedDict([
        ("name", plan.name),
        ("url", absolute_url("/plans/{plan_id}/".format(plan_id=plan.id))),
        ("interval", plan.interval),
        ("interval_count", plan.interval_count),
        ("amount", str(Decimal(plan.amount).quantize(Decimal('0.0000')))),
        ("currency", plan.currency),
        ("trial_period_days", plan.trial_period_days),
        ("generate_after", plan.generate_after),
        ("enabled", plan.enabled),
        ("private", plan.private),
        ("product_code", plan.product_code.value),
        ("metered_features", [
            spec_metered_feature(metered_feature) for metered_feature in plan.metered_features.all()
        ]),
        ("provider", absolute_url("/providers/{provider_id}/".format(provider_id=plan.provider.id)))
    ])
