def spec_discount(discount, subscription=None):
    return {
        'name': discount.name,
        'product_code': discount.product_code.value if discount.product_code else None,
        'percentage': str(discount.percentage),
        'applies_to': discount.applies_to,
        'document_entry_behavior': discount.document_entry_behavior,
        'discount_stacking_type': discount.discount_stacking_type,
        'state': discount.state,
        'start_date': discount.start_date,
        'end_date': discount.end_date,
        'duration_count': discount.duration_count,
        'duration_interval': discount.duration_interval,
        'period_applied_to_subscription': (
            discount.period_applied_to_subscription(subscription) if subscription else None
        ),
        'is_active_for_subscription': discount.is_active_for_subscription(subscription) if subscription else None
    }
