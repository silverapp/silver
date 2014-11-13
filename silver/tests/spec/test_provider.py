import base64

import pytest
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from rest_framework.test import APITestCase
from rest_framework import status, HTTP_HEADER_ENCODING

from silver.models import Provider
from silver.tests.factories import ProviderFactory


class TestProviderEndpoint(APITestCase):

    def setUp(self):
        # TODO: Use factories
        username = 'admin'
        email = 'admin@admin.com'
        password = 'admin'
        self.user = User.objects.create_superuser(username, email, password)

        self.client.force_authenticate(user=self.user)

    def test_list_providers(self):
        ProviderFactory.create_batch(30)

        url = reverse('silver_api:provider-list')
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 30
        assert 'next' in response.data
        assert 'previous' in response.data

    def _filter_providers(self, *args, **kwargs):
        return Provider.objects.filter(*args, **kwargs)

    def test_create_valid_provider(self):
        url = reverse('silver_api:provider-list')
        data = {
            "name": "TestProvider",
            "company": "S.C. Timisoara S.R.L",
            "address_1": "Address",
            "country": "RO",
            "city": "Timisoara",
            "zip_code": "300300"
        }
        response = self.client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data == {
            'id': 1,
            'url':
            'http://testserver/providers/1/',
            'name': u'TestProvider',
            'company': u'S.C. Timisoara S.R.L',
            'email': None,
            'address_1': u'Address',
            'address_2': None,
            'city': u'Timisoara',
            'state': None,
            'zip_code': u'300300',
            'country': u'RO',
            'extra': None
        }
        qs = self._filter_providers()
        assert qs.count() == 1

    def test_create_provider_without_required_fields(self):
        url = reverse('silver_api:provider-list')
        complete_data = {
            "name": "TestProvider",
            'company': u'S.C. Timisoara S.R.L',
            "address_1": "Address",
            "country": "RO",
            "city": "Timisoara",
            "zip_code": "300300"
        }
        required_fields = ['company', 'address_1', 'country', 'city',
                           'zip_code']

        for field in required_fields:
            temp_data = complete_data.copy()
            try:
                temp_data.pop(field)
            except KeyError:
                pytest.xfail('Required field %s for Provider not provided in the test data.' % field)

            response = self.client.post(url, temp_data)

            assert response.status_code == 400
            assert response.data == {field: [u'This field is required.']}

            qs = self._filter_providers()
            assert qs.count() == 0
