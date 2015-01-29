import json

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from silver.models import ProductCode
from silver.tests.factories import (AdminUserFactory, ProviderFactory,
                                    PlanFactory, MeteredFeatureFactory,
                                    ProductCodeFactory)


class TestPlanEndpoint(APITestCase):
    def setUp(self):
        admin_user = AdminUserFactory.create()
        self.client.force_authenticate(user=admin_user)

    def test_create_plan(self):
        url = reverse('plan-list')

        metered_features = MeteredFeatureFactory.create_batch(3)
        mf_urls = []
        for mf in metered_features:
            mf_urls.append(reverse('metered-feature-detail',
                                   kwargs={'pk': mf.pk}))

        feature1_pc = ProductCode.objects.get(id=1).value
        feature2_pc = ProductCode.objects.get(id=2).value
        plan_pc = ProductCode.objects.get(id=3).value
        provider = ProviderFactory.create()
        provider_url = reverse('provider-detail',
                               kwargs={'pk': provider.pk})
        response = self.client.post(url, json.dumps({
            "name": "Hydrogen",
            "interval": "month",
            "interval_count": 1,
            "amount": 149.99,
            "currency": "USD",
            "trial_period_days": 15,
            "generate_after": 86400,
            "enabled": True,
            "private": False,
            "product_code": plan_pc,
            'metered_features': [{
                'name': 'Page Views',
                'unit': '100k',
                'price_per_unit': 0.01,
                'included_units': 0,
                'product_code': feature1_pc
            }, {
                'name': 'VIP Support',
                'price_per_unit': 49.99,
                'included_units': 1,
                'product_code': feature2_pc
            }],
            'provider': provider_url
        }), content_type='application/json')

        assert response.status_code == status.HTTP_201_CREATED

    def test_create_plan_without_required_fields(self):
        url = reverse('plan-list')

        response = self.client.post(url, json.dumps({
            "name": "Hydrogen",
            "interval_count": 1,
            "amount": 149.99,
            "currency": "USD",
            "trial_period_days": 15,
            "generate_after": 86400,
            "enabled": True,
            "private": False,
            'metered_features': []
        }), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_plan(self):
        plan = PlanFactory.create()

        url = reverse('plan-detail', kwargs={'pk': plan.pk})

        response = self.client.patch(url, json.dumps({
            "name": "Hydrogen",
            "generate_after": 86400
        }), content_type='application/json')
        self.assertEqual(response.data['name'], 'Hydrogen')
        self.assertEqual(response.data['generate_after'], 86400)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_patch_plan_non_editable_field(self):
        plan = PlanFactory.create()

        url = reverse('plan-detail', kwargs={'pk': plan.pk})

        response = self.client.patch(url, json.dumps({
            "currency": "DollaDolla"
        }), content_type='application/json')
        self.assertNotEqual(response.data['currency'], 'DollaDolla')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_put_plan(self):
        plan = PlanFactory.create()

        url = reverse('plan-detail', kwargs={'pk': plan.pk})

        response = self.client.put(url)

        self.assertEqual(response.status_code,
                         status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(response.data,
                         {u'detail': u"Method 'PUT' not allowed."})

    def test_get_plan_list(self):
        PlanFactory.create_batch(40)

        url = reverse('plan-list')

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

    def test_get_plan_detail(self):
        plan = PlanFactory.create()

        url = reverse('plan-detail', kwargs={'pk': plan.pk})

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.data, [])

    def test_get_plan_detail_unexisting(self):
        url = reverse('plan-detail', kwargs={'pk': 1})

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_plan(self):
        plan = PlanFactory.create()
        plan.enabled = True
        plan.save()

        url = reverse('plan-detail', kwargs={'pk': 1})

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"deleted": True})

    def test_delete_plan_unexisting(self):
        url = reverse('plan-detail', kwargs={'pk': 1})

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
