# -*- coding: utf-8 -*-
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


from django.core import serializers
import simplejson as json
import pytest
from django.core.urlresolvers import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from silver.models import Provider
from silver.tests.factories import ProviderFactory, AdminUserFactory


class TestProviderEndpoints(APITestCase):

    def setUp(self):
        admin_user = AdminUserFactory.create()
        self.client.force_authenticate(user=admin_user)

    def _filter_providers(self, *args, **kwargs):
        return Provider.objects.filter(*args, **kwargs)

    def test_post_valid_provider(self):
        url = reverse('provider-list')
        data = {
            "name": "TestProviderá",
            "company": "S.C. Timisoará S.R.L",
            "address_1": "Address",
            "country": "RO",
            "city": "Timisoara",
            "zip_code": "300300",
            "flow": "proforma",
            "invoice_series": "TestSeries",
            "invoice_starting_number": 1,
            "proforma_series": "TestSeries",
            "proforma_starting_number": 1,
        }
        response = self.client.post(url, data)

        expected_data = {
            'name': u'TestProviderá',
            'company': u'S.C. Timisoará S.R.L',
            'email': None,
            'address_1': u'Address',
            'address_2': None,
            'city': u'Timisoara',
            'state': None,
            'zip_code': u'300300',
            'country': u'RO',
            'extra': None,
            'flow': 'proforma',
            'invoice_series': 'TestSeries',
            "invoice_starting_number": 1,
            "proforma_series": "TestSeries",
            "proforma_starting_number": 1,
            "meta": {},
        }

        for attr, value in expected_data.iteritems():
            assert response.data[attr] == value

        assert response.status_code == status.HTTP_201_CREATED

        qs = self._filter_providers()
        assert qs.count() == 1

    def test_post_provider_without_required_fields(self):
        url = reverse('provider-list')
        complete_data = {
            "name": "TestProvider",
            'company': u'S.C. Timisoara S.R.L',
            "address_1": "Address",
            "country": "RO",
            "city": "Timisoara",
            "zip_code": "300300",
            "invoice_series": "TheSeries",
            "invoice_starting_number": 300,
            "flow": "proforma",
            "proforma_series": "TheSecondSeries",
            "proforma_starting_number": 360,
        }
        required_fields = ['address_1', 'country', 'city', 'name',
                           'invoice_series', 'invoice_starting_number',
                           'proforma_series', 'proforma_starting_number']

        for field in required_fields:
            temp_data = complete_data.copy()
            try:
                temp_data.pop(field)
            except KeyError:
                pytest.xfail("Required field %s for Provider not provided"
                             " in the test data." % field)

            response = self.client.post(url, temp_data)

            assert response.status_code == 400

            for response_item in response.data.iteritems():
                field_name = response_item[0]
                if field_name in ['id', 'url']:
                    continue

                valid_responses = [
                    (field_name, ['This field may not be blank.']),
                    (field_name, ['This field is required.']),
                    (field_name, ['This field is required as the chosen flow '
                                  'is proforma.'])]
                assert response_item in valid_responses

            qs = self._filter_providers()
            assert qs.count() == 0

    def test_get_providers(self):
        batch_size = 40
        ProviderFactory.create_batch(batch_size)
        url = reverse('provider-list')
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

    def test_POST_bulk_providers(self):
        providers = ProviderFactory.create_batch(5)

        raw_providers = json.loads(serializers.serialize('json', providers))

        serialized_providers = []
        for item in raw_providers:
            serialized_providers.append(item['fields'])

        url = reverse('provider-list')
        request_body = json.dumps(serialized_providers, ensure_ascii=True).encode('utf8')
        response = self.client.post(url, data=request_body,
                                    content_type='application/json')

        assert response.status_code == status.HTTP_201_CREATED
        assert len(response.data) == 5

    def test_get_provider(self):
        ProviderFactory.reset_sequence(1)
        provider = ProviderFactory.create()

        url = reverse('provider-detail', kwargs={'pk': provider.pk})

        response = self.client.get(url)

        assert response.status_code == 200
        expected = {
            'id': provider.pk,
            'url': 'http://testserver/providers/%s/' % provider.pk,
            'name': provider.name,
            'company': provider.company,
            'flow': provider.flow,
            'invoice_series': provider.invoice_series,
            'invoice_starting_number': provider.invoice_starting_number,
            'proforma_series': provider.proforma_series,
            'proforma_starting_number': provider.proforma_starting_number,
            'email': provider.email,
            'address_1': provider.address_1,
            'address_2': provider.address_2,
            'city': provider.city,
            'state': provider.state,
            'zip_code': provider.zip_code,
            'country': provider.country,
            'extra': provider.extra,
            'meta': {u'something': [1, 2]},
        }
        assert response.data == expected

    def test_get_unexisting_provider(self):
        url = reverse('provider-detail', kwargs={'pk': 1})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_put_provider_correctly(self):
        ProviderFactory.reset_sequence(1)
        provider = ProviderFactory.create()

        url = reverse('provider-detail', kwargs={'pk': provider.pk})
        new_data = {
            'id': provider.pk,
            'url': 'http://testserver/providers/%s/' % provider.pk,
            'name': 'TestProvider',
            'company': 'TheNewCompany',
            'email': 'a@a.com',
            'address_1': 'address',
            'city': 'City',
            'zip_code': '1',
            'country': 'RO',
            'flow': 'proforma',
            'invoice_series': 'NewSeries',
            'invoice_starting_number': 1,
            'proforma_series': 'ProformaSeries',
            'proforma_starting_number': 1
            # TODO: add new meta JSON value
        }

        response = self.client.put(url, data=new_data)

        assert response.status_code == status.HTTP_200_OK
        assert response.data == {
            'id': provider.pk,
            'url': 'http://testserver/providers/%s/' % provider.pk,
            'name': 'TestProvider',
            'company': 'TheNewCompany',
            'flow': 'proforma',
            'email': 'a@a.com',
            'address_1': 'address',
            'address_2': u'Addåress21',
            'city': 'City',
            'state': 'State1',
            'zip_code': '1',
            'country': 'RO',
            'extra': 'Extra1',
            'flow': 'proforma',
            'invoice_series': 'NewSeries',
            'invoice_starting_number': 1,
            'proforma_series': 'ProformaSeries',
            'proforma_starting_number': 1,
            'meta': {u'something': [1, 2]},
        }

    def test_put_provider_without_required_field(self):
        """
         .. note::

             The test does not verify each required field, because the test
         test_create_provider_without_required_fields does this and since the
         creation will fail the update will fail too. This is more of a
         sanity test, to check if the correct view is called and if it does
         what's supposed to do for at least one field.
         """

        provider = ProviderFactory.create()

        url = reverse('provider-detail', kwargs={'pk': provider.pk})
        new_data = {
            'id': provider.pk,
            'url': 'http://testserver/providers/%s/' % provider.pk,
            'email': 'a@a.com',
            'address_1': 'address',
            'city': 'City',
            'zip_code': '1',
            'country': 'RO',
            'flow': 'invoice',
            'invoice_series': 'NSeries',
            'invoice_starting_number': 2,
        }

        response = self.client.put(url, data=new_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == {'name': ['This field is required.']}

    def test_patch_provider(self):
        ProviderFactory.reset_sequence(1)
        provider = ProviderFactory.create()

        url = reverse('provider-detail', kwargs={'pk': provider.pk})

        new_data = {
            'company': 'TheNewCompany',  # The changed field
            'address_1': 'Address11',
            'flow': 'proforma',
            'invoice_series': 'InvoiceSeries',
            'invoice_starting_number': 1,
            'proforma_series': 'ProformaSeries',
            'proforma_starting_number': 1,
            'city': 'City1',
            'zip_code': '1',
            'country': u'AL',
        }

        response = self.client.patch(url, data=new_data)

        assert response.status_code == 200
        assert response.data == {
            'id': provider.pk,
            'url': 'http://testserver/providers/%s/' % provider.pk,
            'name': u'Náme1',
            'company': u'TheNewCompany',
            'flow': 'proforma',
            'invoice_series': 'InvoiceSeries',
            'invoice_starting_number': 1,
            'proforma_series': 'ProformaSeries',
            'proforma_starting_number': 1,
            'email': 'provider1@email.com',
            'address_1': 'Address11',
            'address_2': u'Addåress21',
            'city': 'City1',
            'state': 'State1',
            'zip_code': '1',
            'country': u'AL',
            'extra': 'Extra1',
            'meta': {u'something': [1, 2]},
        }

    def test_delete_provider(self):
        provider = ProviderFactory.create()

        url = reverse('provider-detail', kwargs={'pk': provider.pk})
        response = self.client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_unexisting_provider(self):
        url = reverse('provider-detail', kwargs={'pk': 1})
        response = self.client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
