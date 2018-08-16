# Copyright (c) 2017 Presslabs SRL
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
