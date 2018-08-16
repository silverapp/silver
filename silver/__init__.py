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
