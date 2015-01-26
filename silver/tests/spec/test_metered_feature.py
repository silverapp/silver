import json
# from django.core import serializers
import pytest

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase
from silver.tests.factories import (AdminUserFactory, MeteredFeatureFactory,
                                    ProductCodeFactory)



class TestMeteredFeatureEndpoint(APITestCase):
    def setUp(self):
        admin_user = AdminUserFactory.create()
        self.client.force_authenticate(user=admin_user)
        self.complete_data = {
            "name": "Page Views",
            "unit": "100k",
            "price_per_unit": 0.05,
            "included_units": 0,
            "product_code": ProductCodeFactory.create().value
        }

    def test_create_post_metered_feature(self):
        url = reverse('metered-feature-list')
        response = self.client.post(url, json.dumps(self.complete_data),
                                    content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        expected = self.complete_data
        expected.update({'url': 'http://testserver/metered-features/1/'})

        assert expected == response.data

    def test_create_post_metered_feature_without_required_field(self):
        url = reverse('metered-feature-list')

        required_fields = ['name', 'price_per_unit', 'included_units']
        for field in required_fields:
            temp_data = self.complete_data.copy()
            try:
                temp_data.pop(field)
            except KeyError:
                pytest.xfail('Metered Feature required field %s not provided in'
                             'the complete test data.' % field)

            response = self.client.post(url, json.dumps(temp_data),
                                        content_type='application/json')

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            assert (response.data == {field: ['This field may not be blank.']}
                    or response.data == {field: ['This field is required.']})
    """
    #def test_create_post_metered_feature_bulk(self):
        #mfs = MeteredFeatureFactory.create_batch(7)

        #raw_mfs = json.loads(serializers.serialize('json', mfs))

        #serialized_mfs = []
        #for item in raw_mfs:
            #serialized_mfs.append(item['fields'])

        #url = reverse('metered-feature-list')

        #response = self.client.post(url, data=json.dumps(serialized_mfs),
                                    #content_type='application/json')

        #self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        #self.assertEqual(len(response.data), 7)
    """
    def test_get_metered_feature_detail(self):
        metered_feature = MeteredFeatureFactory.create()

        url = reverse('metered-feature-detail',
                      kwargs={'pk': metered_feature.pk})

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.data, [])

    def test_get_metered_feature_list(self):
        MeteredFeatureFactory.create_batch(40)
        url = reverse('silver_api:metered-feature-list')

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

    def test_get_metered_feature_unexisting(self):
        url = reverse('metered-feature-detail',
                      kwargs={'pk': 42})

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data, {u'detail': u'Not found'})

    def test_delete_metered_feature(self):
        MeteredFeatureFactory.create()

        url = reverse('metered-feature-detail', kwargs={'pk': 1})

        response = self.client.delete(url)

        self.assertEqual(response.status_code,
                         status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(response.data,
                         {u'detail': u"Method 'DELETE' not allowed."})

    def test_edit_put_metered_feature(self):
        MeteredFeatureFactory.create()

        url = reverse('metered-feature-detail', kwargs={'pk': 1})

        response = self.client.put(url)

        self.assertEqual(response.status_code,
                         status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(response.data,
                         {u'detail': u"Method 'PUT' not allowed."})

    def test_edit_patch_metered_feature(self):
        MeteredFeatureFactory.create()

        url = reverse('metered-feature-detail', kwargs={'pk': 1})

        response = self.client.patch(url)

        self.assertEqual(response.status_code,
                         status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(response.data,
                         {u'detail': u"Method 'PATCH' not allowed."})
