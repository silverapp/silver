def spec_discount(discount, subscription=None):
    return {
        'id': discount.id,
        'name': discount.name,
        'product_code': discount.product_code.value if discount.product_code else None,
        'percentage': str(discount.percentage),
        'applies_to': discount.applies_to,
        'only_for_product_codes': [product_code.value for product_code in discount.filter_product_codes.all()],
        'document_entry_behavior': discount.document_entry_behavior,
        'discount_stacking_type': discount.discount_stacking_type,
        'enabled': discount.enabled,
        'start_date': discount.start_date,
        'end_date': discount.end_date,
        'duration_count': discount.duration_count,
        'duration_interval': discount.duration_interval,
        'period_applied_to_subscription': (
            discount.period_applied_to_subscription(subscription) if subscription else None
        ),
        'is_active_for_subscription': discount.is_active_for_subscription(subscription) if subscription else None
    }
