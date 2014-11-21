import json

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase
from silver.tests.factories import (AdminUserFactory, ProviderFactory,
                                    PlanFactory, MeteredFeatureFactory)


class TestPlanEndpoint(APITestCase):
    def setUp(self):
        admin_user = AdminUserFactory.create()
        self.client.force_authenticate(user=admin_user)

    def test_create_plan(self):
        url = reverse('silver_api:plan-list')

        metered_features = MeteredFeatureFactory.create_batch(3)
        mf_urls = []
        for mf in metered_features:
            mf_urls.append(reverse('silver_api:metered-feature-detail',
                                  kwargs={'pk': mf.pk}))

        provider = ProviderFactory.create()
        provider_url = reverse('silver_api:provider-detail',
                               kwargs={'pk': provider.pk})
        response = self.client.post(url, json.dumps({
            "name": "Hydrogen",
            "interval": "month",
            "interval_count": 1,
            "amount": 149.99,
            "currency": "USD",
            "trial_period_days": 15,
            "due_days": 10,
            "generate_after": 86400,
            "enabled": True,
            "private": False,
            "product_code": "1234",
            'metered_features': mf_urls,
            'provider': provider_url
        }), content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_plan_without_required_fields(self):
        url = reverse('silver_api:plan-list')
        response = self.client.post(url, json.dumps({
            "name": "Hydrogen",
            "interval_count": 1,
            "amount": 149.99,
            "currency": "USD",
            "trial_period_days": 15,
            "due_days": 10,
            "generate_after": 86400,
            "enabled": True,
            "private": False,
            'metered_features': [
                {
                    'name': '100k PageViews',
                    'price_per_unit': 10,
                    'included_units': 5
                }
            ]
        }), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_plan_list(self):
        PlanFactory.create()
        url = reverse('silver_api:plan-list')

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.data, [])

    def test_get_plan_detail(self):
        PlanFactory.create()
        url = reverse('silver_api:plan-detail', kwargs={'pk': 1})

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.data, [])

    def test_get_plan_detail_unexisting(self):
        url = reverse('silver_api:plan-detail', kwargs={'pk': 1})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_plan(self):
        plan = PlanFactory.create()
        plan.enabled = True
        plan.save()

        url = reverse('silver_api:plan-detail', kwargs={'pk': 1})

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"deleted": False})

    def test_delete_plan_unexisting(self):
        url = reverse('silver_api:plan-detail', kwargs={'pk': 1})

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
