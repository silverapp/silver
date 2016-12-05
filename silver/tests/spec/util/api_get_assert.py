from rest_framework import status
from rest_framework.test import APITestCase

from silver.tests.factories import AdminUserFactory


class APIGetAssert(APITestCase):
    serializer_class = None

    def setUp(self):
        admin_user = AdminUserFactory.create()
        self.client.force_authenticate(user=admin_user)

    def assert_get_data(self, url, expected_data):
        many = isinstance(expected_data, list)
        response = self.client.get(url, format='json')
        request = response.wsgi_request
        expected = self.serializer_class(expected_data,
                                         context={'request': request},
                                         many=many).data

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, expected)
