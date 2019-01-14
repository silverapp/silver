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

from __future__ import absolute_import

import json
import pytest

from django.urls import reverse
from django.utils.encoding import force_text

from rest_framework.test import APITestCase
from rest_framework import status

from silver.models import Provider
from silver.tests.factories import ProviderFactory, AdminUserFactory
from silver.tests.utils import build_absolute_test_url


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

        for attr, value in expected_data.items():
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

            for response_item in response.data.items():
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
            ('Link', '<' + full_url + '?page=2>; rel="next", ' +
             '<' + full_url + '?page=1>; rel="first", ' +
             '<' + full_url + '?page=2> rel="last"')

        response = self.client.get(url + '?page=2')

        assert response.status_code == status.HTTP_200_OK
        assert response._headers['link'] == \
            ('Link', '<' + full_url + '>; rel="prev", ' +
             '<' + full_url + '?page=1>; rel="first", ' +
             '<' + full_url + '?page=2> rel="last"')

    def test_POST_bulk_providers(self):
        request_body = [
            {
                u'city': u'Cit\u01770',
                u'proforma_series': u'ProformaSeries',
                u'name': u'N\xe1me0',
                u'extra': u'Extra0',
                u'default_document_state': u'draft',
                u'country': u'AD',
                u'company': u'Comp\xe1ny0',
                u'flow': u'proforma',
                u'state': u'State0',
                u'invoice_starting_number': 1,
                u'phone': None,
                u'live': True,
                u'meta': {"something": [0, 1]},
                u'address_1': u'Add\xe3ress10',
                u'address_2': u'Add\xe5ress20',
                u'proforma_starting_number': 1,
                u'invoice_series': u'InvoiceSeries',
                u'email': u'provider0@email.com',
                u'zip_code': u'0'
            },
            {
                u'city': u'Cit\u01771',
                u'proforma_series': u'ProformaSeries',
                u'name': u'N\xe1me1',
                u'extra': u'Extra1',
                u'default_document_state': u'draft',
                u'country': u'AD',
                u'company': u'Comp\xe1ny1',
                u'flow': u'proforma',
                u'state': u'State1',
                u'invoice_starting_number': 1,
                u'phone': None,
                u'live': True,
                u'meta': {"something": [2, 3]},
                u'address_1': u'Add\xe3ress11',
                u'address_2': u'Add\xe5ress21',
                u'proforma_starting_number': 1,
                u'invoice_series': u'InvoiceSeries',
                u'email': u'provider10@email.com',
                u'zip_code': u'1'
            }
        ]

        url = reverse('provider-list')
        response = self.client.post(url, data=json.dumps(request_body),
                                    content_type='application/json')

        assert response.status_code == status.HTTP_201_CREATED
        assert len(response.data) == 2

    def test_get_provider(self):
        ProviderFactory.reset_sequence(1)
        provider = ProviderFactory.create()

        url = reverse('provider-detail', kwargs={'pk': provider.pk})

        response = self.client.get(url)

        assert response.status_code == 200

        self_url = build_absolute_test_url(url)
        expected = {
            'id': provider.pk,
            'url': self_url,
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

        self_url = build_absolute_test_url(url)
        assert response.data == {
            'id': provider.pk,
            'url': self_url,
            'name': new_data['name'],
            'company': new_data['company'],
            'flow': provider.flow,
            'email': new_data['email'],
            'address_1': new_data['address_1'],
            'address_2': provider.address_2,
            'city': new_data['city'],
            'state': provider.state,
            'zip_code': new_data['zip_code'],
            'country': new_data['country'],
            'extra': provider.extra,
            'flow': new_data['flow'],
            'invoice_series': new_data['invoice_series'],
            'invoice_starting_number': new_data['invoice_starting_number'],
            'proforma_series': new_data['proforma_series'],
            'proforma_starting_number': new_data['proforma_starting_number'],
            'meta': provider.meta,
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

        self_url = build_absolute_test_url(url)
        assert response.data == {
            'id': provider.pk,
            'url': self_url,
            'name': provider.name,
            'company': new_data['company'],
            'flow': new_data['flow'],
            'invoice_series': new_data['invoice_series'],
            'invoice_starting_number': new_data['invoice_starting_number'],
            'proforma_series': new_data['proforma_series'],
            'proforma_starting_number': new_data['proforma_starting_number'],
            'email': provider.email,
            'address_1': new_data['address_1'],
            'address_2': provider.address_2,
            'city': new_data['city'],
            'state': provider.state,
            'zip_code': new_data['zip_code'],
            'country': new_data['country'],
            'extra': provider.extra,
            'meta': provider.meta,
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
