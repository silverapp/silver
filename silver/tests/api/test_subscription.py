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

import datetime
import json
from collections import OrderedDict

from django.conf import settings
from django.utils.timezone import utc

from freezegun import freeze_time

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from silver.models import Subscription
from silver.tests.api.specs.subscription import spec_subscription
from silver.fixtures.factories import (AdminUserFactory, CustomerFactory,
                                       PlanFactory, SubscriptionFactory,
                                       MeteredFeatureFactory)


class TestSubscriptionEndpoint(APITestCase):
    def setUp(self):
        admin_user = AdminUserFactory.create()
        self.client.force_authenticate(user=admin_user)

    def test_create_subscription(self):
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

        subscription = Subscription.objects.get(id=response.data['id'])
        assert response.data == spec_subscription(subscription)

    def test_create_subscription_reference(self):
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

        subscription = Subscription.objects.get(id=response.data['id'])
        assert response.data == spec_subscription(subscription)

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

        subscription = Subscription.objects.get(id=response.data['id'])
        assert response.data == spec_subscription(subscription)

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

        assert response.status_code == status.HTTP_200_OK, response.data
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

    @freeze_time('2017-02-05')
    def test_cancel_subscription(self):
        subscription = SubscriptionFactory.create()
        subscription.activate()
        subscription.save()

        url = reverse('sub-cancel',
                      kwargs={'subscription_pk': subscription.pk,
                              'customer_pk': subscription.customer.pk})

        response = self.client.post(url, json.dumps({
            "when": "end_of_billing_cycle"}), content_type='application/json')

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data == {'state': Subscription.STATES.CANCELED}

        subscription = Subscription.objects.get(pk=subscription.pk)
        assert subscription.state == Subscription.STATES.CANCELED
        assert subscription.cancel_date == datetime.date(2017, 2, 28)

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

        assert subscription.state == Subscription.STATES.INACTIVE

    def test_end_subscription(self):
        subscription = SubscriptionFactory.create()
        subscription.activate()
        subscription.save()

        url = reverse('sub-cancel',
                      kwargs={'subscription_pk': subscription.pk,
                              'customer_pk': subscription.customer.pk})

        response = self.client.post(url, json.dumps({
            "when": "now"}), content_type='application/json')

        assert response.status_code == status.HTTP_200_OK, response.data
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

        assert response.status_code == status.HTTP_200_OK, response.data
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
        SubscriptionFactory.create_batch(settings.API_PAGE_SIZE * 2, customer=customer)

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

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response['link'] == \
            ('<' + full_url + '?page=2>; rel="next", ' +
             '<' + full_url + '?page=1>; rel="first", ' +
             '<' + full_url + '?page=2> rel="last"')

        response = self.client.get(url + '?page=2')

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response['link'] == \
            ('<' + full_url + '>; rel="prev", ' +
             '<' + full_url + '?page=1>; rel="first", ' +
             '<' + full_url + '?page=2> rel="last"')

        for subscription_data in response.data:
            subscription = Subscription.objects.get(id=subscription_data['id'])
            assert subscription_data == spec_subscription(subscription)

    def test_get_subscription_list_reference_filter(self):
        customer = CustomerFactory.create()
        subscriptions = SubscriptionFactory.create_batch(3, customer=customer)

        url = reverse('subscription-list',
                      kwargs={'customer_pk': customer.pk})

        references = [subscription.reference for subscription in subscriptions]

        reference = '?reference=' + references[0]
        response = self.client.get(url + reference)

        assert len(response.data) == 1
        assert response.status_code == status.HTTP_200_OK, response.data

        reference = '?reference=' + ','.join(references)
        response = self.client.get(url + reference)

        assert len(response.data) == 3
        assert response.status_code == status.HTTP_200_OK, response.data

        reference = '?reference=' + ','.join(references[:-1]) + ',invalid'
        response = self.client.get(url + reference)
        assert len(response.data) == 2
        assert response.status_code == status.HTTP_200_OK, response.data

        for subscription_data in response.data:
            subscription = Subscription.objects.get(id=subscription_data['id'])
            assert subscription_data == spec_subscription(subscription)

    def test_get_subscription_detail(self):
        subscription = SubscriptionFactory.create()

        url = reverse('subscription-detail',
                      kwargs={'subscription_pk': subscription.pk,
                              'customer_pk': subscription.customer.pk})

        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data == spec_subscription(subscription, detail=True)

    def test_get_subscription_detail_unexisting(self):
        customer = CustomerFactory.create()
        url = reverse('subscription-detail',
                      kwargs={'subscription_pk': 42,
                              'customer_pk': customer.pk})

        response = self.client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data == {u'detail': u'Not found.'}

    @freeze_time('2022-05-02')
    def test_create_subscription_mf_units_log_active_sub(self):
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
            "consumed_units": '150.0000',
            "date": date,
            "update_type": "absolute"
        }), content_type='application/json')

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data == {
            "consumed_units": '150.0000',
            'annotation': None,
            'start_datetime': '2022-05-02T00:00:00Z',
            'end_datetime': '2022-05-31T23:59:59Z',
        }

        # A successive request

        response = self.client.patch(url, json.dumps({
            "consumed_units": 29,
            "date": date,
            "update_type": "relative"
        }), content_type='application/json')

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data == {
            "consumed_units": '179.0000',
            'annotation': None,
            'start_datetime': '2022-05-02T00:00:00Z',
            'end_datetime': '2022-05-31T23:59:59Z',
        }

    @freeze_time('2022-05-02')
    def test_create_subscription_mf_units_log_with_annotation(self):
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
            "consumed_units": '150.0000',
            "date": date,
            "update_type": "absolute",
            "annotation": "test",
        }), content_type='application/json')

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data == {
            "consumed_units": '150.0000',
            'annotation': "test",
            'start_datetime': '2022-05-02T00:00:00Z',
            'end_datetime': '2022-05-31T23:59:59Z',
        }

        # A successive relative patch request

        response = self.client.patch(url, json.dumps({
            "consumed_units": 29,
            "date": date,
            "update_type": "relative",
            "annotation": "test",
        }), content_type='application/json')

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data == {
            "consumed_units": '179.0000',
            'annotation': "test",
            'start_datetime': '2022-05-02T00:00:00Z',
            'end_datetime': '2022-05-31T23:59:59Z',
        }

        # A third patch request on a different annotation
        response = self.client.patch(url, json.dumps({
            "consumed_units": 42,
            "date": date,
            "update_type": "relative",
            "annotation": "different",
        }), content_type='application/json')

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data == {
            "consumed_units": '42.0000',
            'annotation': "different",
            'start_datetime': '2022-05-02T00:00:00Z',
            'end_datetime': '2022-05-31T23:59:59Z',
        }

        # A fourth patch request with no annotation
        response = self.client.patch(url, json.dumps({
            "consumed_units": 99,
            "date": date,
            "update_type": "absolute",
        }), content_type='application/json')

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data == {
            "consumed_units": '99.0000',
            'annotation': None,
            'start_datetime': '2022-05-02T00:00:00Z',
            'end_datetime': '2022-05-31T23:59:59Z',
        }

        # A fifth GET request for all buckets
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data == [
            OrderedDict([
                ('consumed_units', '99.0000'),
                ('start_datetime', '2022-05-02T00:00:00Z'),
                ('end_datetime', '2022-05-31T23:59:59Z'),
                ('annotation', None)
            ]),
            OrderedDict([
                ('consumed_units', '42.0000'),
                ('start_datetime', '2022-05-02T00:00:00Z'),
                ('end_datetime', '2022-05-31T23:59:59Z'),
                ('annotation', 'different')
            ]),
            OrderedDict([
                ('consumed_units', '179.0000'),
                ('start_datetime', '2022-05-02T00:00:00Z'),
                ('end_datetime', '2022-05-31T23:59:59Z'),
                ('annotation', 'test')
            ]),
        ]

    @freeze_time('2022-05-15')
    def test_create_subscription_mf_units_log_with_end_log(self):
        subscription = SubscriptionFactory.create(
            start_date=datetime.date(2022, 5, 2),
        )
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
            "consumed_units": '150.0000',
            "date": date,
            "update_type": "absolute",
        }), content_type='application/json')

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data == {
            "consumed_units": '150.0000',
            'annotation': None,
            'start_datetime': '2022-05-02T00:00:00Z',
            'end_datetime': '2022-05-31T23:59:59Z',
        }

        # A second relative patch request with end bucket

        response = self.client.patch(url, json.dumps({
            "consumed_units": 29,
            "date": date,
            "update_type": "relative",
            "end_log": True,
        }), content_type='application/json')

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data == {
            "consumed_units": '179.0000',
            'annotation': None,
            'start_datetime': '2022-05-02T00:00:00Z',
            'end_datetime': '2022-05-15T00:00:00Z',
        }

        # A third patch request matching a new bucket in the same month

        response = self.client.patch(url, json.dumps({
            "consumed_units": 50,
            "date": str(datetime.date.today() + datetime.timedelta(days=1)),
            "update_type": "absolute",
            "end_log": True,
        }), content_type='application/json')

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data == {
            "consumed_units": '50.0000',
            'annotation': None,
            'start_datetime': '2022-05-15T00:00:01Z',
            'end_datetime': '2022-05-31T23:59:59Z',
        }

        # A fourth GET request for all buckets
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data == [
            OrderedDict(
                [('consumed_units', '179.0000'),
                 ('start_datetime', '2022-05-02T00:00:00Z'),
                 ('end_datetime', '2022-05-15T00:00:00Z'),
                 ('annotation', None)]
            ),
            OrderedDict(
                [('consumed_units', '50.0000'),
                 ('start_datetime', '2022-05-15T00:00:01Z'),
                 ('end_datetime', '2022-05-31T23:59:59Z'),
                 ('annotation', None)]
            ),
        ]

    @freeze_time('2022-05-02')
    def test_create_subscription_mf_units_log_sub_canceled_at_end_of_month(self):
        subscription = SubscriptionFactory.create(state=Subscription.STATES.CANCELED,
                                                  start_date=datetime.date(2022, 5, 2),
                                                  cancel_date=datetime.date(2022, 5, 31))
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
            "consumed_units": '150.0000',
            "date": date,
            "update_type": "absolute"
        }), content_type='application/json')

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data == {
            "consumed_units": '150.0000',
            'annotation': None,
            'start_datetime': '2022-05-02T00:00:00Z',
            'end_datetime': '2022-05-31T23:59:59Z',
        }

        # A successive request

        response = self.client.patch(url, json.dumps({
            "consumed_units": 29,
            "date": date,
            "update_type": "relative"
        }), content_type='application/json')

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data == {
            "consumed_units": '179.0000',
            'annotation': None,
            'start_datetime': '2022-05-02T00:00:00Z',
            'end_datetime': '2022-05-31T23:59:59Z',
        }

    @freeze_time('2022-05-02')
    def test_create_subscription_mf_units_log_with_sub_canceled_now(self):
        subscription = SubscriptionFactory.create(state=Subscription.STATES.CANCELED,
                                                  start_date=datetime.date(2022, 5, 2),
                                                  cancel_date=datetime.date(2022, 5, 2))
        metered_feature = MeteredFeatureFactory.create()
        subscription.plan.metered_features.add(metered_feature)

        url = reverse('mf-log-units',
                      kwargs={'subscription_pk': subscription.pk,
                              'customer_pk': subscription.customer.pk,
                              'mf_product_code': metered_feature.product_code})

        date = str(datetime.date.today())

        response = self.client.patch(url, json.dumps({
            "consumed_units": '150.0000',
            "date": date,
            "update_type": "absolute"
        }), content_type='application/json')

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data == {
            "consumed_units": '150.0000',
            'annotation': None,
            'start_datetime': '2022-05-02T00:00:00Z',
            'end_datetime': '2022-05-31T23:59:59Z',
        }

        # A successive request

        response = self.client.patch(url, json.dumps({
            "consumed_units": 29,
            "date": date,
            "update_type": "relative"
        }), content_type='application/json')

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data == {
            "consumed_units": '179.0000',
            'annotation': None,
            'start_datetime': '2022-05-02T00:00:00Z',
            'end_datetime': '2022-05-31T23:59:59Z',
        }

    @freeze_time('2017-01-01')
    def test_create_subscription_mf_units_log_with_sub_canceled_before(self):
        subscription = SubscriptionFactory.create(state=Subscription.STATES.CANCELED,
                                                  start_date=datetime.date(2016, 1, 1),
                                                  cancel_date=datetime.date(2016, 12, 31))
        metered_feature = MeteredFeatureFactory.create()
        subscription.plan.metered_features.add(metered_feature)

        url = reverse('mf-log-units',
                      kwargs={'subscription_pk': subscription.pk,
                              'customer_pk': subscription.customer.pk,
                              'mf_product_code': metered_feature.product_code})

        date = str(datetime.date.today())

        response = self.client.patch(url, json.dumps({
            "consumed_units": '150.0000',
            "date": date,
            "update_type": "absolute"
        }), content_type='application/json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == {"detail": "Date is out of bounds."}

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

    def test_create_subscription_mf_units_log_with_inactive_sub(self):
        subscription = SubscriptionFactory.create()
        metered_feature = MeteredFeatureFactory.create()
        subscription.plan.metered_features.add(metered_feature)

        url = reverse('mf-log-units',
                      kwargs={'subscription_pk': subscription.pk,
                              'customer_pk': subscription.customer.pk,
                              'mf_product_code': metered_feature.product_code})

        response = self.client.patch(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {'detail': 'Subscription is inactive.'}

    def test_create_subscription_mf_units_log_with_ended_sub(self):
        subscription = SubscriptionFactory.create(state=Subscription.STATES.ENDED)
        metered_feature = MeteredFeatureFactory.create()
        subscription.plan.metered_features.add(metered_feature)

        url = reverse('mf-log-units',
                      kwargs={'subscription_pk': subscription.pk,
                              'customer_pk': subscription.customer.pk,
                              'mf_product_code': metered_feature.product_code})

        response = self.client.patch(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {'detail': 'Subscription is ended.'}

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
            "consumed_units": '150.0000',
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

        data = {}

        response = self.client.patch(url, json.dumps(data),
                                     content_type='application/json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == {
            "consumed_units": ['This field is required.'],
            'date': ['This field is required.'],
            'update_type': ['This field is required.']}
