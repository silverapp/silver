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


import datetime
import json

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from silver.models import Subscription
from silver.tests.factories import (AdminUserFactory, CustomerFactory,
                                    PlanFactory, SubscriptionFactory,
                                    MeteredFeatureFactory)


class TestSubscriptionEndpoint(APITestCase):
    def setUp(self):
        admin_user = AdminUserFactory.create()
        self.client.force_authenticate(user=admin_user)

    def test_create_post_subscription(self):
        plan = PlanFactory.create()
        customer = CustomerFactory.create()

        plan_url = reverse('plan-detail', kwargs={'pk': plan.pk})

        url = reverse('subscription-list', kwargs={'customer_pk': customer.pk})

        response = self.client.post(url, json.dumps({
            "plan": plan_url,
            "trial_end": '2014-12-07',
            "start_date": '2014-11-19'
        }), content_type='application/json')
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_post_subscription_reference(self):
        plan = PlanFactory.create()
        customer = CustomerFactory.create()

        plan_url = reverse('plan-detail', kwargs={'pk': plan.pk})

        url = reverse('subscription-list', kwargs={'customer_pk': customer.pk})

        test_reference = 'test reference'
        response = self.client.post(url, json.dumps({
            "plan": plan_url,
            "start_date": '2014-11-19',
            "reference": test_reference,
        }), content_type='application/json')

        assert response.status_code == status.HTTP_201_CREATED

        assert response.data["reference"] == test_reference

    def test_create_post_subscription_description(self):
        plan = PlanFactory.create()
        customer = CustomerFactory.create()

        plan_url = reverse('plan-detail', kwargs={'pk': plan.pk})

        url = reverse('subscription-list', kwargs={'customer_pk': customer.pk})

        test_description = 'test description'
        response = self.client.post(url, json.dumps({
            "plan": plan_url,
            "start_date": '2014-11-19',
            "description": test_description,
        }), content_type='application/json')

        assert response.status_code == status.HTTP_201_CREATED

        assert response.data["description"] == test_description

    def test_create_post_subscription_with_invalid_trial_end(self):
        plan = PlanFactory.create()
        customer = CustomerFactory.create()

        plan_url = reverse('plan-detail', kwargs={'pk': plan.pk})

        url = reverse('subscription-list', kwargs={'customer_pk': customer.pk})

        response = self.client.post(url, json.dumps({
            "plan": plan_url,
            "trial_end": '2014-11-07',
            "start_date": '2014-11-19'
        }), content_type='application/json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_activate_subscription(self):
        subscription = SubscriptionFactory.create()
        url = reverse('sub-activate',
                      kwargs={'subscription_pk': subscription.pk,
                              'customer_pk': subscription.customer.pk})

        response = self.client.post(url, content_type='application/json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data == {'state': 'active'}

    def test_activate_subscription_from_terminal_state(self):
        subscription = SubscriptionFactory.create()
        subscription.activate()
        subscription.cancel(when=Subscription.CANCEL_OPTIONS.NOW)
        subscription.save()

        url = reverse('sub-activate',
                      kwargs={'subscription_pk': subscription.pk,
                              'customer_pk': subscription.customer.pk})

        response = self.client.post(url, content_type='application/json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == {
            'error': u'Cannot activate subscription from canceled state.'
        }

    def test_cancel_subscription(self):
        subscription = SubscriptionFactory.create()
        subscription.activate()
        subscription.save()

        url = reverse('sub-cancel',
                      kwargs={'subscription_pk': subscription.pk,
                              'customer_pk': subscription.customer.pk})

        response = self.client.post(url, json.dumps({
            "when": "end_of_billing_cycle"}), content_type='application/json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data == {'state': Subscription.STATES.CANCELED}

    def test_cancel_subscription_from_terminal_state(self):
        subscription = SubscriptionFactory.create()

        url = reverse('sub-cancel',
                      kwargs={'subscription_pk': subscription.pk,
                              'customer_pk': subscription.customer.pk})

        response = self.client.post(url, json.dumps({
            "when": "end_of_billing_cycle"}), content_type='application/json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == {
            'error': u'Cannot cancel subscription from inactive state.'
        }

    def test_end_subscription(self):
        subscription = SubscriptionFactory.create()
        subscription.activate()
        subscription.save()

        url = reverse('sub-cancel',
                      kwargs={'subscription_pk': subscription.pk,
                              'customer_pk': subscription.customer.pk})

        response = self.client.post(url, json.dumps({
            "when": "now"}), content_type='application/json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data == {'state': 'canceled'}

    def test_end_subscription_from_terminal_state(self):
        subscription = SubscriptionFactory.create()

        url = reverse('sub-cancel',
                      kwargs={'subscription_pk': subscription.pk,
                              'customer_pk': subscription.customer.pk})

        response = self.client.post(url, json.dumps({
            "when": "now"}), content_type='application/json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == {
            'error': u'Cannot cancel subscription from inactive state.'
        }

    def test_reactivate_subscription(self):
        subscription = SubscriptionFactory.create()
        subscription.activate()
        subscription.cancel(when=Subscription.CANCEL_OPTIONS.NOW)
        subscription.save()

        url = reverse('sub-reactivate',
                      kwargs={'subscription_pk': subscription.pk,
                              'customer_pk': subscription.customer.pk})

        response = self.client.post(url, content_type='application/json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data == {'state': Subscription.STATES.ACTIVE}

    def test_reactivate_subscription_from_terminal_state(self):
        subscription = SubscriptionFactory.create()
        subscription.activate()
        subscription.cancel(when=Subscription.CANCEL_OPTIONS.NOW)
        subscription.end()
        subscription.save()

        url = reverse('sub-reactivate',
                      kwargs={'subscription_pk': subscription.pk,
                              'customer_pk': subscription.customer.pk})

        response = self.client.post(url, content_type='application/json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == {
            'error': u'Cannot reactivate subscription from ended state.'
        }

    def test_get_subscription_list(self):
        customer = CustomerFactory.create()
        SubscriptionFactory.create_batch(40, customer=customer)

        url = reverse('subscription-list',
                      kwargs={'customer_pk': customer.pk})

        response = self.client.get(url)

        full_url = None
        for field in response.data:
            full_url = field.get('url', None)
            if full_url:
                break
        if full_url:
            domain = full_url.split('/')[2]
            full_url = full_url.split(domain)[0] + domain + url

        assert response.status_code == status.HTTP_200_OK
        assert response._headers['link'] == \
            ('Link', '<' + full_url + '?page=2; rel="next">, ' +
             '<' + full_url + '?page=1; rel="first">, ' +
             '<' + full_url + '?page=2; rel="last">')

        response = self.client.get(url + '?page=2')

        assert response.status_code == status.HTTP_200_OK
        assert response._headers['link'] == \
            ('Link', '<' + full_url + '; rel="prev">, ' +
             '<' + full_url + '?page=1; rel="first">, ' +
             '<' + full_url + '?page=2; rel="last">')

    def test_get_subscription_list_reference_filter(self):
        customer = CustomerFactory.create()
        subscriptions = SubscriptionFactory.create_batch(3, customer=customer)

        url = reverse('subscription-list',
                      kwargs={'customer_pk': customer.pk})

        references = [subscription.reference for subscription in subscriptions]

        reference = '?reference=' + references[0]
        response = self.client.get(url + reference)

        assert len(response.data) == 1
        assert response.status_code == status.HTTP_200_OK

        reference = '?reference=' + ','.join(references)
        response = self.client.get(url + reference)

        assert len(response.data) == 3
        assert response.status_code == status.HTTP_200_OK

        reference = '?reference=' + ','.join(references[:-1]) + ',invalid'
        response = self.client.get(url + reference)
        assert len(response.data) == 2
        assert response.status_code == status.HTTP_200_OK

    def test_get_subscription_detail(self):
        subscription = SubscriptionFactory.create()

        url = reverse('subscription-detail',
                      kwargs={'subscription_pk': subscription.pk,
                              'customer_pk': subscription.customer.pk})

        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data != []

    def test_get_subscription_detail_unexisting(self):
        customer = CustomerFactory.create()
        url = reverse('subscription-detail',
                      kwargs={'subscription_pk': 42,
                              'customer_pk': customer.pk})

        response = self.client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data == {u'detail': u'Not found.'}

    def test_create_subscription_mf_units_log(self):
        subscription = SubscriptionFactory.create()
        metered_feature = MeteredFeatureFactory.create()

        subscription.plan.metered_features.add(metered_feature)

        subscription.activate()
        subscription.save()

        url = reverse('mf-log-units',
                      kwargs={'subscription_pk': subscription.pk,
                              'customer_pk': subscription.customer.pk,
                              'mf_product_code': metered_feature.product_code})

        date = str(datetime.date.today())

        response = self.client.patch(url, json.dumps({
            "count": 150,
            "date": date,
            "update_type": "absolute"
        }), content_type='application/json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data == {'count': 150}

        response = self.client.patch(url, json.dumps({
            "count": 29,
            "date": date,
            "update_type": "relative"
        }), content_type='application/json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data == {'count': 179}

    def test_create_subscription_mf_units_log_with_unexisting_mf(self):
        subscription = SubscriptionFactory.create()

        subscription.activate()
        subscription.save()

        url = reverse('mf-log-units',
                      kwargs={'subscription_pk': subscription.pk,
                              'customer_pk': subscription.customer.pk,
                              'mf_product_code': '1234'})

        response = self.client.patch(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data == {'detail': 'Metered Feature Not found.'}

    def test_create_subscription_mf_units_log_with_unactivated_sub(self):
        subscription = SubscriptionFactory.create()
        metered_feature = MeteredFeatureFactory.create()
        subscription.plan.metered_features.add(metered_feature)

        url = reverse('mf-log-units',
                      kwargs={'subscription_pk': subscription.pk,
                              'customer_pk': subscription.customer.pk,
                              'mf_product_code': metered_feature.product_code})

        response = self.client.patch(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {'detail': 'Subscription is not active.'}

    def test_create_subscription_mf_units_log_with_invalid_date(self):
        subscription = SubscriptionFactory.create()
        metered_feature = MeteredFeatureFactory.create()

        subscription.plan.metered_features.add(metered_feature)

        subscription.activate()
        subscription.save()

        url = reverse('mf-log-units',
                      kwargs={'subscription_pk': subscription.pk,
                              'customer_pk': subscription.customer.pk,
                              'mf_product_code': metered_feature.product_code})

        response = self.client.patch(url, json.dumps({
            "count": 150,
            "date": "2008-12-24",
            "update_type": "absolute"
        }), content_type='application/json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == {'detail': 'Date is out of bounds.'}

    def test_create_subscription_mf_units_log_with_insufficient_data(self):
        subscription = SubscriptionFactory.create()
        metered_feature = MeteredFeatureFactory.create()

        subscription.plan.metered_features.add(metered_feature)

        subscription.activate()
        subscription.save()

        url = reverse('mf-log-units',
                      kwargs={'subscription_pk': subscription.pk,
                              'customer_pk': subscription.customer.pk,
                              'mf_product_code': metered_feature.product_code})

        data = {
            "count": 150,
            "date": "2008-12-24",
            "update_type": "absolute"
        }

        for field in data:
            data_copy = data.copy()
            data_copy.pop(field)

            response = self.client.patch(url, json.dumps(data_copy),
                                         content_type='application/json')

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert response.data == {field: ['This field is required.']}
