import json
import pytest

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase
from silver.tests.factories import AdminUserFactory, CustomerFactory


class TestCustomerEndpoint(APITestCase):
    def setUp(self):
        admin_user = AdminUserFactory.create()
        self.client.force_authenticate(user=admin_user)

    complete_data = {
        "customer_reference": "123456",
        "name": "Batman",
        "company": "Wayne Enterprises",
        "email": "bruce@wayneenterprises.com",
        "address_1": "Batcave St.",
        "address_2": "Some other address info",
        "city": "Gotham",
        "state": "SomeState",
        "zip_code": "1111",
        "country": "US",
        "extra": "What is there more to say?",
        "sales_tax_name": "VAT",
        "sales_tax_percent": '3.00'
    }

    def test_create_post_customer(self):
        url = reverse('customer-list')

        response = self.client.post(url, json.dumps(self.complete_data),
                                    content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_post_customer_without_required_field(self):
        url = reverse('customer-list')

        required_fields = ['address_1', 'city', 'zip_code', 'country']

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
            assert (response.data == {field: ['This field may not be blank.']}
                    or response.data == {field: ['This field is required.']})

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

    def test_get_customer_detail(self):
        customer = CustomerFactory.create()

        url = reverse('customer-detail',
                      kwargs={'pk': customer.pk})

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.data, [])

    def test_get_customer_detail_unexisting(self):
        url = reverse('customer-detail',
                      kwargs={'pk': 42})

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data, {u'detail': u'Not found'})

    def test_delete_customer(self):
        customer = CustomerFactory.create()

        url = reverse('customer-detail', kwargs={'pk': customer.pk})
        response = self.client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_unexisting_customer(self):
        url = reverse('customer-detail', kwargs={'pk': 42})
        response = self.client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_edit_put_customer(self):
        CustomerFactory.create()

        changed_data = self.complete_data.copy()
        unchanged_fields = ['email', 'address_2', 'name']
        for field in unchanged_fields:
            changed_data.pop(field)

        url = reverse('customer-detail', kwargs={'pk': 1})

        response = self.client.put(url, data=changed_data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response.data.pop('id')
        response.data.pop('url')
        for field in response.data:
            if field not in unchanged_fields:
                self.assertEqual(response.data[field],
                                 self.complete_data[field])

    def test_edit_patch_customer(self):
        CustomerFactory.create()

        changed_data = self.complete_data.copy()
        unchanged_fields = ['email', 'zip_code', 'company']
        for field in unchanged_fields:
            changed_data.pop(field)

        url = reverse('customer-detail', kwargs={'pk': 1})

        response = self.client.patch(url, data=changed_data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response.data.pop('id')
        response.data.pop('url')
        for field in response.data:
            if field not in unchanged_fields:
                self.assertEqual(response.data[field],
                                 self.complete_data[field])
