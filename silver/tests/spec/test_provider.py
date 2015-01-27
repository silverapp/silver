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
            "name": "TestProvider",
            "company": "S.C. Timisoara S.R.L",
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

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data == {
            'id': 1,
            'url': 'http://testserver/providers/1/',
            'name': u'TestProvider',
            'company': u'S.C. Timisoara S.R.L',
            'email': '',
            'address_1': u'Address',
            'address_2': '',
            'city': u'Timisoara',
            'state': '',
            'zip_code': u'300300',
            'country': u'RO',
            'extra': '',
            'flow': 'proforma',
            'invoice_series': 'TestSeries',
            "invoice_starting_number": 1,
            "proforma_series": "TestSeries",
            "proforma_starting_number": 1,
        }
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
        }
        required_fields = ['company', 'address_1', 'country', 'city',
                           'zip_code', 'flow', 'invoice_series',
                           'invoice_starting_number']

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
                valid_responses = [
                    (field_name, ['This field may not be blank.']),
                    (field_name, ['This field is required.'])]
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
        assert response._headers['x-result-count'] == ('X-Result-Count',
                                                       str(batch_size))
        assert response._headers['link'] == \
            ('Link', '<' + full_url + '?page=2>; rel="next", ' +
             '<' + full_url + '?page=2>; rel="last", ' +
             '<' + full_url + '?page=1>; rel="first"')

        response = self.client.get(url + '?page=2')

        assert response.status_code == status.HTTP_200_OK
        assert response._headers['x-result-count'] == ('X-Result-Count',
                                                       str(batch_size))
        assert response._headers['link'] == \
            ('Link', '<' + full_url + '?page=1>; rel="prev", ' +
             '<' + full_url + '?page=2>; rel="last", ' +
             '<' + full_url + '?page=1>; rel="first"')

    """
    #def test_POST_bulk_providers(self):
        #providers = ProviderFactory.create_batch(5)

        #raw_providers = json.loads(serializers.serialize('json', providers))

        #serialized_providers = []
        #for item in raw_providers:
            #serialized_providers.append(item['fields'])

        #url = reverse('provider-list')
        #response = self.client.post(url, data=json.dumps(serialized_providers),
                                    #content_type='application/json')

        #assert response.status_code == status.HTTP_201_CREATED
        #assert len(response.data) == 5
    """

    def test_GET_provider(self):
        ProviderFactory.reset_sequence(1)
        ProviderFactory.create()

        url = reverse('provider-detail', kwargs={'pk': 1})

        response = self.client.get(url)

        assert response.status_code == 200
        assert response.data == {
            'id': 1,
            'url': 'http://testserver/providers/1/',
            'name': 'Provider1',
            'company': 'Company1',
            'invoice_series': 'TestSeries',
            'flow': 'proforma',
            'email': None,
            'address_1': 'Address_11',
            'address_2': None,
            'city': 'City1',
            'state': None,
            'zip_code': '1',
            'country': u'RO',
            'extra': None
        }

    def test_GET_unexisting_provider(self):
        url = reverse('provider-detail', kwargs={'pk': 1})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_PUT_provider_correctly(self):
        ProviderFactory.create()

        url = reverse('provider-detail', kwargs={'pk': 1})
        new_data = {
            'id': 1,
            'url': 'http://testserver/providers/1/',
            'name': 'TestProvider',
            'company': 'TheNewCompany',
            'invoice_series': 'NewSeries',
            'email': 'a@a.com',
            'address_1': 'address',
            'city': 'City',
            'zip_code': '1',
            'country': 'RO',
        }

        response = self.client.put(url, data=new_data)

        assert response.status_code == status.HTTP_200_OK
        assert response.data == {
            'id': 1,
            'url': 'http://testserver/providers/1/',
            'name': 'TestProvider',
            'company': 'TheNewCompany',
            'invoice_series': 'NewSeries',
            'flow': 'proforma',
            'email': 'a@a.com',
            'address_1': 'address',
            'address_2': '',
            'city': 'City',
            'state': '',
            'zip_code': '1',
            'country': 'RO',
            'extra': ''
        }

    def test_PUT_provider_without_required_field(self):
        """
         .. note::

             The test does not verify each required field, because the test
         test_create_provider_without_required_fields does this and since the
         creation will fail the update will fail too. This is more of a
         sanity test, to check if the correct view is called and if it does
         what's supposed to do for at least one field.
         """

        ProviderFactory.create()

        url = reverse('provider-detail', kwargs={'pk': 1})
        new_data = {
            'id': 1,
            'url': 'http://testserver/providers/1/',
            'name': 'TestProvider',
            'email': 'a@a.com',
            'invoice_series': 'NSeries',
            'address_1': 'address',
            'city': 'City',
            'zip_code': '1',
            'country': 'RO',
        }

        response = self.client.put(url, data=new_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == {'company': ['This field may not be blank.']}

    def test_DELETE_provider(self):
        ProviderFactory.create()

        url = reverse('provider-detail', kwargs={'pk': 1})
        response = self.client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_DELETE_unexisting_provider(self):
        url = reverse('provider-detail', kwargs={'pk': 1})
        response = self.client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
