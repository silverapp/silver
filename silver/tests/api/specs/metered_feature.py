from collections import OrderedDict


def spec_metered_feature(metered_feature):
    return OrderedDict([
        ("name", metered_feature.name),
        ("unit", metered_feature.unit),
        ("price_per_unit", metered_feature.price_per_unit),
        ("included_units", metered_feature.included_units),
        ("product_code", metered_feature.product_code.value)
    ])
