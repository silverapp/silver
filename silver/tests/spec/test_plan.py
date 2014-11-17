# -*- coding: utf-8 -*-
# vim: ft=python:sw=4:ts=4:sts=4:et:
import json

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APITestCase


class TestPlanEndpoint(APITestCase):
    fixtures = ['test_data.json']

    def setUp(self):
        self.client = APIClient()

        self.user_staff = User.objects.create_user(
            'staff', email='a@b.c', password='abc')
        self.user_staff.is_staff = True
        self.user_staff.save()

        self.token_staff = Token.objects.create(user=self.user_staff)
        self.token_staff.save()

    def test_create_plan(self):
        self.client.force_authenticate(self.user_staff, self.token_staff)

        response = self.client.put('/plans/', json.dumps({
            "name": "Hydrogen",
            "interval": "month",
            "interval_count": 1,
            "amount": 149.99,
            "currency": "USD",
            "trial_period_days": 15,
            "due_days": 10,
            "generate_after": 86400,
            "enabled": True,
            "private": False,
            "product_code": "1234",
            'metered_features': [
                {
                    'name': '100k PageViews',
                    'price_per_unit': 10,
                    'included_units': 5
                }
            ],
        }), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_get_plan_list(self):
        self.client.force_authenticate(self.user_staff, self.token_staff)

        response = self.client.get('/plans/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.data, [])

    def test_get_plan_detail(self):
        self.client.force_authenticate(self.user_staff, self.token_staff)
        response = self.client.get('/plans/1/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.data, [])
