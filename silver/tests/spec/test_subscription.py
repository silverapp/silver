import datetime
import json

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase
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

        plan_url = reverse('silver_api:plan-detail', kwargs={'pk': plan.pk})
        customer_url = reverse('silver_api:customer-detail',
                               kwargs={'pk': customer.pk})

        url = reverse('silver_api:subscription-list')

        response = self.client.post(url, json.dumps({
            "plan": plan_url,
            "customer": customer_url,
            "trial_end": '2014-12-07',
            "start_date": '2014-11-19'
        }), content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_post_subscription_with_invalid_trial_end(self):
        plan = PlanFactory.create()
        customer = CustomerFactory.create()

        plan_url = reverse('silver_api:plan-detail', kwargs={'pk': plan.pk})
        customer_url = reverse('silver_api:customer-detail',
                               kwargs={'pk': customer.pk})

        url = reverse('silver_api:subscription-list')

        response = self.client.post(url, json.dumps({
            "plan": plan_url,
            "customer": customer_url,
            "trial_end": '2014-11-07',
            "start_date": '2014-11-19'
        }), content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_activate_subscription(self):
        subscription = SubscriptionFactory.create()
        url = reverse('silver_api:sub-activate',
                      kwargs={'sub': subscription.pk})

        response = self.client.post(url, content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'state': 'active'})

    def test_activate_subscription_from_wrong_state(self):
        subscription = SubscriptionFactory.create()
        subscription.activate()
        subscription.cancel()
        subscription.save()

        url = reverse('silver_api:sub-activate',
                      kwargs={'sub': subscription.pk})

        response = self.client.post(url, content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data,
            {'error': u'Cannot activate subscription from canceled state.'}
        )

    def test_cancel_subscription(self):
        subscription = SubscriptionFactory.create()
        subscription.activate()
        subscription.save()

        url = reverse('silver_api:sub-cancel',
                      kwargs={'sub': subscription.pk})

        response = self.client.post(url, json.dumps({
            "when": "end_of_billing_cycle"}), content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'state': 'canceled'})

    def test_cancel_subscription_from_wrong_state(self):
        subscription = SubscriptionFactory.create()

        url = reverse('silver_api:sub-cancel',
                      kwargs={'sub': subscription.pk})

        response = self.client.post(url, json.dumps({
            "when": "end_of_billing_cycle"}), content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data,
            {'error': u'Cannot cancel subscription from inactive state.'}
        )

    def test_end_subscription(self):
        subscription = SubscriptionFactory.create()
        subscription.activate()
        subscription.save()

        url = reverse('silver_api:sub-cancel',
                      kwargs={'sub': subscription.pk})

        response = self.client.post(url, json.dumps({
            "when": "now"}), content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'state': 'ended'})

    def test_end_subscription_from_wrong_state(self):
        subscription = SubscriptionFactory.create()

        url = reverse('silver_api:sub-cancel',
                      kwargs={'sub': subscription.pk})

        response = self.client.post(url, json.dumps({
            "when": "now"}), content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data,
            {'error': u'Cannot cancel subscription from inactive state.'}
        )

    def test_reactivate_subscription(self):
        subscription = SubscriptionFactory.create()
        subscription.activate()
        subscription.cancel()
        subscription.save()

        url = reverse('silver_api:sub-reactivate',
                      kwargs={'sub': subscription.pk})

        response = self.client.post(url, content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'state': 'active'})

    def test_reactivate_subscription_from_wrong_state(self):
        subscription = SubscriptionFactory.create()
        subscription.activate()
        subscription.cancel()
        subscription.end()
        subscription.save()

        url = reverse('silver_api:sub-reactivate',
                      kwargs={'sub': subscription.pk})

        response = self.client.post(url, content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data,
            {'error': u'Cannot reactivate subscription from ended state.'}
        )

    def test_get_subscription_list(self):
        SubscriptionFactory.create_batch(4)

        url = reverse('silver_api:subscription-list')

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.data, [])

    def test_get_subscription_detail(self):
        subscription = SubscriptionFactory.create()

        url = reverse('silver_api:subscription-detail',
                      kwargs={'pk': subscription.pk})

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.data, [])

    def test_get_subscription_detail_unexisting(self):
        url = reverse('silver_api:subscription-detail',
                      kwargs={'pk': 42})

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data, {u'detail': u'Not found'})

    def test_create_subscription_mf_units_log(self):
        subscription = SubscriptionFactory.create()
        metered_feature = MeteredFeatureFactory.create()

        subscription.plan.metered_features.add(metered_feature)

        subscription.activate()
        subscription.save()

        url = reverse('silver_api:mf-log-list',
                      kwargs={'sub': subscription.pk,
                              'mf': metered_feature.pk})

        date = str(datetime.date.today() + datetime.timedelta(days=3))

        response = self.client.patch(url, json.dumps({
            "count": 150,
            "date": date,
            "update_type": "absolute"
        }), content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'count': 150})

        response = self.client.patch(url, json.dumps({
            "count": 29,
            "date": date,
            "update_type": "relative"
        }), content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'count': 179})

    def test_create_subscription_mf_units_log_with_unexisting_mf(self):
        subscription = SubscriptionFactory.create()

        subscription.activate()
        subscription.save()

        url = reverse('silver_api:mf-log-list',
                      kwargs={'sub': subscription.pk,
                              'mf': 42})

        response = self.client.patch(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data, {'detail': 'Not found'})

    def test_create_subscription_mf_units_log_with_unactivated_sub(self):
        subscription = SubscriptionFactory.create()
        metered_feature = MeteredFeatureFactory.create()
        subscription.plan.metered_features.add(metered_feature)

        url = reverse('silver_api:mf-log-list',
                      kwargs={'sub': subscription.pk,
                              'mf': metered_feature.pk})

        response = self.client.patch(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data,
                         {'detail': 'Subscription is not active'})

    def test_create_subscription_mf_units_log_with_invalid_date(self):
        subscription = SubscriptionFactory.create()
        metered_feature = MeteredFeatureFactory.create()

        subscription.plan.metered_features.add(metered_feature)

        subscription.activate()
        subscription.save()

        url = reverse('silver_api:mf-log-list',
                      kwargs={'sub': subscription.pk,
                              'mf': metered_feature.pk})

        response = self.client.patch(url, json.dumps({
            "count": 150,
            "date": "2008-12-24",
            "update_type": "absolute"
        }), content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'detail': 'Date is out of bounds'})
