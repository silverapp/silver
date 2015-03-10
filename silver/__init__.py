# -*- coding: utf-8 -*-
__version__ = '0.1'

HOOK_EVENTS = {
    # 'any.event.name': 'App.Model.Action' (created/updated/deleted)
    'customer.created': 'silver.Customer.created',
    'customer.updated': 'silver.Customer.updated',
    'customer.deleted': 'silver.Customer.deleted',

    'plan.created': 'silver.Plan.created',
    'plan.updated': 'silver.Plan.updated',
    'plan.deleted': 'silver.Plan.deleted',

    'subscription.created': 'silver.Subscription.created',
    'subscription.updated': 'silver.Subscription.updated',
    'subscription.deleted': 'silver.Subscription.deleted',

    'provider.created': 'silver.Provider.created',
    'provider.updated': 'silver.Provider.updated',
    'provider.deleted': 'silver.Provider.deleted',

    'invoice.created': 'silver.Invoice.created',
    'invoice.updated': 'silver.Invoice.updated',
    'invoice.deleted': 'silver.Invoice.deleted',

    'proforma.created': 'silver.Proforma.created',
    'proforma.updated': 'silver.Proforma.updated',
    'proforma.deleted': 'silver.Proforma.deleted',
}
