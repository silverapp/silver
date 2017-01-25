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


import json
import pytest

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from silver.models import Customer
from silver.tests.factories import AdminUserFactory, CustomerFactory


class TestCustomerEndpoints(APITestCase):
    def setUp(self):
        admin_user = AdminUserFactory.create()
        self.client.force_authenticate(user=admin_user)
        self.complete_data = {
            "customer_reference": "123456",
            "first_name": "Bruce",
            "last_name": "Wayne",
            "company": "Wayne Enterprises",
            "email": "bruce@wayneenterprises.com",
            "address_1": "Batcave St.",
            "address_2": "Some other address info",
            "city": "Gotham",
            "state": "SomeState",
            "zip_code": "1111",
            "country": "US",
            "phone": "+40000000000",
            "currency": "USD",
            "extra": "What is there more to say?",
            "sales_tax_number": "RO5555555",
            "sales_tax_name": "VAT",
            "sales_tax_percent": '3.00',
            "payment_due_days": 5,
            "consolidated_billing": False,
            "meta": {'water': ['plants', '5']},
            "payment_methods": u'http://testserver/customers/1/payment_methods/',
            "transactions": u'http://testserver/customers/1/transactions/'
        }

    def test_create_post_customer(self):
        url = reverse('customer-list')

        response = self.client.post(url, json.dumps(self.complete_data),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_post_customer_without_required_field(self):
        url = reverse('customer-list')

        required_fields = ['first_name', 'last_name', 'address_1', 'city',
                           'country']

        for field in required_fields:
            temp_data = self.complete_data.copy()
            try:
                temp_data.pop(field)
            except KeyError:
                pytest.xfail('Customer required field %s not provided in the'
                             'complete test data.' % field)

            response = self.client.post(url, json.dumps(temp_data),
                                        content_type='application/json')

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            assert (response.data == {field: ['This field may not be blank.']} or
                    response.data == {field: ['This field is required.']})

    def test_get_customer_list(self):
        CustomerFactory.create_batch(40)

        url = reverse('customer-list')

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

    def test_get_customer_detail(self):
        customer = CustomerFactory.create()

        url = reverse('customer-detail',
                      kwargs={'customer_pk': customer.pk})

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.data, [])
        self.assertEqual(response.data['phone'], customer.phone)

    def test_get_customer_detail_unexisting(self):
        url = reverse('customer-detail',
                      kwargs={'customer_pk': 42})

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data, {u'detail': u'Not found.'})

    def test_delete_customer(self):
        customer = CustomerFactory.create()

        url = reverse('customer-detail', kwargs={'customer_pk': customer.pk})
        response = self.client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert Customer.objects.all().count() == 0

    def test_delete_unexisting_customer(self):
        url = reverse('customer-detail', kwargs={'customer_pk': 42})
        response = self.client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_edit_put_customer(self):
        customer = CustomerFactory.create()

        changed_data = self.complete_data.copy()

        unchanged_fields = ['email', 'address_2']
        ignore_fields = ['url', 'id', 'subscriptions', 'payment_methods',
                         'transactions']
        for field in unchanged_fields:
            changed_data.pop(field)

        url = reverse('customer-detail', kwargs={'customer_pk': customer.pk})

        response = self.client.put(url, data=json.dumps(changed_data),
                                   content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for e in ignore_fields:
            response.data.pop(e)
        for field in response.data:
            if field not in unchanged_fields:
                self.assertEqual(response.data[field],
                                 self.complete_data[field])

    def test_edit_patch_customer(self):
        customer = CustomerFactory.create()

        changed_data = self.complete_data.copy()
        unchanged_fields = ['email', 'zip_code', 'company', 'phone',
                            'payment_due_days']
        ignore_fields = ['url', 'id', 'subscriptions', 'payment_methods',
                         'transactions']
        for field in unchanged_fields:
            changed_data.pop(field)

        url = reverse('customer-detail', kwargs={'customer_pk': customer.pk})

        response = self.client.patch(url, data=json.dumps(changed_data),
                                     content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for e in ignore_fields:
            response.data.pop(e)
        for field in response.data:
            if field not in unchanged_fields:
                self.assertEqual(response.data[field],
                                 self.complete_data[field])
