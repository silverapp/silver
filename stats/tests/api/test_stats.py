from decimal import Decimal

import datetime
import pytest

from silver.models import BillingLog
from stats.stats import Stats

try:
    from django.urls import reverse
except ImportError:
    from django.core.urlresolvers import reverse

from rest_framework import status


@pytest.mark.django_db
def test_stats_billing_log_correct_url(api_client):
    url = reverse('billing_log_stats')
    response = api_client.get(url, {'result_type': 'total',
                                    'modifier': 'include_unused_plans'})
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_stats_documents_correct_url(api_client):
    url = reverse('document_stats')
    response = api_client.get(url, {'result_type': 'amount',
                                    'granulations_issue_date': 'month',
                                    'granulations_currency': True})
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_stats_transactions_correct_url(api_client):
    url = reverse('transaction_stats')
    response = api_client.get(url, {'result_type': 'amount',
                                    'granulations_issue_date': 'year',
                                    'granulations_currency': True})
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_stats_billing_log_view_is_correct(api_client, create_subscription):
    url = reverse('billing_log_stats')
    response = api_client.get(url, {'result_type': 'total',
                                    'granulation_plan': True,
                                    'granulation_customer': True})

    lista = [{'name': 'plan', 'value': None}, {'name': 'customer', 'value': None}]
    stats = Stats(BillingLog.objects.all(), 'total', None, lista)
    for i in BillingLog.objects.all():
        print i.subscription.customer.first_name, i.subscription.plan
    print stats.validate()

    assert response.data == [
        {'currency': u'USD', 'values': [{'total': Decimal('20.00'),
                                         'billing_date': datetime.date(2017, 1, 31), 'id': 2}],
         'plan': u'Hydrogen', 'customer_name': u'Harry Potter'},
        {'currency': u'RON', 'values': [{'total': Decimal('10.00'),
                                         'billing_date': datetime.date(2017, 1, 11), 'id': 1}],
         'plan': u'Oxygen', 'customer_name': u'Harry Potter'},
        {'currency': u'USD', 'values': [{'total': Decimal('30.00'),
                                         'billing_date': datetime.date(2017, 2, 20), 'id': 4}],
         'plan': u'Enterprise', 'customer_name': u'Ron Weasley'},
        {'currency': u'RON', 'values': [{'total': Decimal('20.00'),
                                         'billing_date': datetime.date(2017, 1, 31), 'id': 3},
                                        {'total': Decimal('20.00'),
                                         'billing_date': datetime.date(2017, 1, 31), 'id': 3}],
         'plan': u'Oxygen', 'customer_name': u'Ron Weasley'}]


@pytest.mark.django_db
def test_stats_document_view_is_correct(api_client, create_document):
    url = reverse('document_stats')
    response = api_client.get(url, {'result_type': 'amount',
                                    'granulation_issue_date': 'month',
                                    'granulation_customer': True})

    assert response.data == [
        {'currency': u'RON', 'issue_date': '2017 Aug', 'values': [{'total': Decimal('101.00'),
                                                                   'id': 1}],
         'customer_name': u'Harry Potter'},
        {'currency': u'RON', 'issue_date': '2017 Aug', 'values': [{'total': 0, 'id': 2},
                                                                  {'total': Decimal('202.00'),
                                                                   'id': 3}],
         'customer_name': u'Ron Weasley'},
        {'currency': u'RON', 'issue_date': '2017 Jul', 'values': [{'total': Decimal('303.00'),
                                                                   'id': 4}],
         'customer_name': u'Ron Weasley'}
    ]


@pytest.mark.django_db
def test_stats_transaction_view_is_correct(api_client, create_transaction):
    url = reverse('transaction_stats')
    response = api_client.get(url, {'result_type': 'amount',
                                    'granulation_created_at': 'month',
                                    'granulation_customer': True})

    assert response.data == [
        {'currency': u'RON', 'created_at': '2017 Jul', 'values': [{'total': Decimal('20.00'),
                                                                   'id': 3}],
         'customer_name': u'Hermione Granger'},
        {'currency': u'RON', 'created_at': '2017 Sep', 'values': [{'total': Decimal('10.00'),
                                                                   'id': 1}],
         'customer_name': u'Hermione Granger'},
        {'currency': u'RON', 'created_at': '2017 Jul', 'values': [{'total': Decimal('15.00'),
                                                                   'id': 2},
                                                                  {'total': Decimal('20.00'),
                                                                   'id': 4}],
         'customer_name': u'Ron Weasley'}
    ]
