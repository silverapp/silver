# Copyright (c) 2015 Presslabs SRL
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import

from collections import OrderedDict
from decimal import Decimal

from django.urls import reverse

from silver.tests.api.specs.metered_feature import spec_metered_feature
from silver.tests.api.utils.path import absolute_url


def spec_plan(plan):
    return OrderedDict([
        ("name", plan.name),
        ("url", absolute_url(reverse("plan-detail", args=[plan.id]))),
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
        ("provider", absolute_url(reverse("provider-detail", args=[plan.provider.id])))
    ])
