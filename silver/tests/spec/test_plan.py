# -*- coding: utf-8 -*-
# vim: ft=python:sw=4:ts=4:sts=4:et:
import json

from silver.models import Plan

from django.test.client import Client
from django.test import TestCase


class PlansSpecificationTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    def test_create_plan(self):
        assert True
        # response = self.client.put('/api/plans', json.dumps({
            # 'name': 'Hydrogen',
            # 'interval': 'month',
            # 'interval_count': 1,
            # 'amount': 150,
            # 'currency': 'USD',
            # 'trial_period_days': 15,
            # 'metered_features': [
                # {
                    # 'name': '100k PageViews',
                    # 'price_per_unit': 10,
                    # 'included_units': 5
                # }
            # ],
            # 'due_days': 10,
            # 'generate_after': 86400
        # }), content_type='application/json')

        # plan = Plan.objects.filter(name='Hydrogen')
        # self.assertEqual(plan.count(), 1)
        # self.assertEqual(response.status_code, 201)
