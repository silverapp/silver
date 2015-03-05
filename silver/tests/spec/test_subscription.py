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

        plan_url = reverse('plan-detail', kwargs={'pk': plan.pk})

        url = reverse('subscription-list', kwargs={'customer_pk': customer.pk})

        response = self.client.post(url, json.dumps({
            "plan": plan_url,
            "trial_end": '2014-12-07',
            "start_date": '2014-11-19'
        }), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

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

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_activate_subscription(self):
        subscription = SubscriptionFactory.create()
        url = reverse('sub-activate',
                      kwargs={'subscription_pk': subscription.pk,
                              'customer_pk': subscription.customer.pk})

        response = self.client.post(url, content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'state': 'active'})

    def test_activate_subscription_from_wrong_state(self):
        subscription = SubscriptionFactory.create()
        subscription.activate()
        subscription.cancel()
        subscription.save()

        url = reverse('sub-activate',
                      kwargs={'subscription_pk': subscription.pk,
                              'customer_pk': subscription.customer.pk})

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

        url = reverse('sub-cancel',
                      kwargs={'subscription_pk': subscription.pk,
                              'customer_pk': subscription.customer.pk})

        response = self.client.post(url, json.dumps({
            "when": "end_of_billing_cycle"}), content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'state': 'canceled'})

    def test_cancel_subscription_from_wrong_state(self):
        subscription = SubscriptionFactory.create()

        url = reverse('sub-cancel',
                      kwargs={'subscription_pk': subscription.pk,
                              'customer_pk': subscription.customer.pk})

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

        url = reverse('sub-cancel',
                      kwargs={'subscription_pk': subscription.pk,
                              'customer_pk': subscription.customer.pk})

        response = self.client.post(url, json.dumps({
            "when": "now"}), content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'state': 'ended'})

    def test_end_subscription_from_wrong_state(self):
        subscription = SubscriptionFactory.create()

        url = reverse('sub-cancel',
                      kwargs={'subscription_pk': subscription.pk,
                              'customer_pk': subscription.customer.pk})

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

        url = reverse('sub-reactivate',
                      kwargs={'subscription_pk': subscription.pk,
                              'customer_pk': subscription.customer.pk})

        response = self.client.post(url, content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'state': 'active'})

    def test_reactivate_subscription_from_wrong_state(self):
        subscription = SubscriptionFactory.create()
        subscription.activate()
        subscription.cancel()
        subscription.end()
        subscription.save()

        url = reverse('sub-reactivate',
                      kwargs={'subscription_pk': subscription.pk,
                              'customer_pk': subscription.customer.pk})

        response = self.client.post(url, content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data,
            {'error': u'Cannot reactivate subscription from ended state.'}
        )

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
        assert response._headers['x-result-count'] == ('X-Result-Count', '40')
        assert response._headers['link'] == \
            ('Link', '<' + full_url + '?page=2>; rel="next", ' +
             '<' + full_url + '?page=2>; rel="last", ' +
             '<' + full_url + '?page=1>; rel="first"')

        response = self.client.get(url + '?page=2')

        assert response.status_code == status.HTTP_200_OK
        assert response._headers['x-result-count'] == ('X-Result-Count', '40')
        assert response._headers['link'] == \
            ('Link', '<' + full_url + '?page=1>; rel="prev", ' +
             '<' + full_url + '?page=2>; rel="last", ' +
             '<' + full_url + '?page=1>; rel="first"')

    def test_get_subscription_detail(self):
        subscription = SubscriptionFactory.create()

        url = reverse('subscription-detail',
                      kwargs={'subscription_pk': subscription.pk,
                              'customer_pk': subscription.customer.pk})

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.data, [])

    def test_get_subscription_detail_unexisting(self):
        customer = CustomerFactory.create()
        url = reverse('subscription-detail',
                      kwargs={'subscription_pk': 42,
                              'customer_pk': customer.pk})

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data, {u'detail': u'Not found'})

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

        url = reverse('mf-log-units',
                      kwargs={'subscription_pk': subscription.pk,
                              'customer_pk': subscription.customer.pk,
                              'mf_product_code': '1234'})

        response = self.client.patch(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data, {'detail': 'Not found'})

    def test_create_subscription_mf_units_log_with_unactivated_sub(self):
        subscription = SubscriptionFactory.create()
        metered_feature = MeteredFeatureFactory.create()
        subscription.plan.metered_features.add(metered_feature)

        url = reverse('mf-log-units',
                      kwargs={'subscription_pk': subscription.pk,
                              'customer_pk': subscription.customer.pk,
                              'mf_product_code': metered_feature.product_code})

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

        url = reverse('mf-log-units',
                      kwargs={'subscription_pk': subscription.pk,
                              'customer_pk': subscription.customer.pk,
                              'mf_product_code': metered_feature.product_code})

        response = self.client.patch(url, json.dumps({
            "count": 150,
            "date": "2008-12-24",
            "update_type": "absolute"
        }), content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'detail': 'Date is out of bounds'})

    def test_subscription_mf_units_log_intervals(self):
        subscription = SubscriptionFactory.create()
        metered_feature = MeteredFeatureFactory.create()

        subscription.plan.metered_features.add(metered_feature)

        subscription.start_date = datetime.date(year=2015, month=2, day=17)
        subscription.activate()
        subscription.save()

        # Monthly
        subscription.plan.interval = 'month'
        subscription.plan.interval_count = 1
        subscription.plan.save()

        subscription.trial_end = (subscription.start_date +
                                  datetime.timedelta(days=15))

        start_date = subscription.start_date
        assert start_date == subscription.bucket_start_date(
            reference_date=datetime.date(year=2015, month=2, day=17))

        end_date = datetime.date(year=2015, month=2, day=28)
        assert end_date == subscription.bucket_end_date(
            reference_date=datetime.date(year=2015, month=2, day=23))

        start_date = datetime.date(year=2015, month=3, day=1)
        assert start_date == subscription.bucket_start_date(
            reference_date=datetime.date(year=2015, month=3, day=1))

        end_date = datetime.date(year=2015, month=3, day=4)
        assert end_date == subscription.bucket_end_date(
            reference_date=datetime.date(year=2015, month=3, day=1))

        start_date = datetime.date(year=2015, month=3, day=5)
        assert start_date == subscription.bucket_start_date(
            reference_date=datetime.date(year=2015, month=3, day=5))

        end_date = datetime.date(year=2015, month=3, day=31)
        assert end_date == subscription.bucket_end_date(
            reference_date=datetime.date(year=2015, month=3, day=22))

        start_date = datetime.date(year=2015, month=4, day=1)
        assert start_date == subscription.bucket_start_date(
            reference_date=datetime.date(year=2015, month=4, day=5))

        end_date = datetime.date(year=2015, month=4, day=30)
        assert end_date == subscription.bucket_end_date(
            reference_date=datetime.date(year=2015, month=4, day=22))
