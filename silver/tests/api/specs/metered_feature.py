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


def spec_metered_feature(metered_feature):
    return OrderedDict([
        ("name", metered_feature.name),
        ("unit", metered_feature.unit),
        ("price_per_unit", metered_feature.price_per_unit),
        ("included_units", metered_feature.included_units),
        ("product_code", metered_feature.product_code.value)
    ])
