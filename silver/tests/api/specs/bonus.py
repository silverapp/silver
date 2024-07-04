def spec_bonus(bonus, subscription=None):
    return {
        'id': bonus.id,
        'name': bonus.name,
        'product_code': bonus.product_code.value if bonus.product_code else None,
        'amount': str(bonus.amount) if bonus.amount else None,
        'amount_percentage': str(bonus.amount_percentage) if bonus.amount_percentage else None,
        'applies_to': bonus.applies_to,
        'enabled': bonus.enabled,
        'start_date': bonus.start_date,
        'end_date': bonus.end_date,
        'duration_count': bonus.duration_count,
        'duration_interval': bonus.duration_interval,
        'period_applied_to_subscription': (
            bonus.period_applied_to_subscription(subscription) if subscription else None
        ),
        'is_active_for_subscription': bonus.is_active_for_subscription(subscription) if subscription else None
    }
