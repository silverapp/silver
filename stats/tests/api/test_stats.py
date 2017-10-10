from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status

from silver.models import Subscription, Transaction, Invoice, BillingLog
from stats.stats import Stats


@pytest.mark.django_db
def test_stats_subscriptions_correct_url(api_client):
    url = reverse('subscription_stats')
    response = api_client.get(url, {'result_type': 'estimated_income',
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
def test_stats_subscription_view_is_correct(api_client, create_subscription):
    url = reverse('subscription_stats')
    response = api_client.get(url, {'result_type': 'estimated_income',
                                    'granulation_plan': True,
                                    'granulation_customer': True})

    assert response.data == [{'currency': u'USD', 'values': [{'total': Decimal('65.00'), 'id': 3}],
                              'plan': u'Enterprise', 'customer_name': u'Harry Potter'},
                             {'currency': u'USD', 'values': [{'total': Decimal('105.00'), 'id': 5}],
                              'plan': u'Hydrogen', 'customer_name': u'Harry Potter'},
                             {'currency': u'RON', 'values': [{'total': Decimal('25.00'), 'id': 1},
                                                             {'total': Decimal('145.00'), 'id': 7}],
                              'plan': u'Oxygen', 'customer_name': u'Harry Potter'},
                             {'currency': u'USD', 'values': [{'total': Decimal('125.00'), 'id': 6}],
                              'plan': u'Enterprise', 'customer_name': u'Ron Weasley'},
                             {'currency': u'USD', 'values': [{'total': Decimal('45.00'), 'id': 2}],
                              'plan': u'Hydrogen', 'customer_name': u'Ron Weasley'},
                             {'currency': u'RON', 'values': [{'total': Decimal('85.00'), 'id': 4}],
                              'plan': u'Oxygen', 'customer_name': u'Ron Weasley'}
                             ]


@pytest.mark.django_db
def test_stats_document_view_is_correct(api_client, create_document):
    url = reverse('document_stats')
    response = api_client.get(url, {'result_type': 'amount',
                                    'granulation_issue_date': 'month',
                                    'granulation_customer': True})

    assert response.data == [
        {'currency': u'RON', 'issue_date': '2017 Aug', 'values': [{'total': Decimal('101.00'), 'id': 1}],
         'customer_name': u'Harry Potter'},
        {'currency': u'RON', 'issue_date': '2017 Aug', 'values': [{'total': 0, 'id': 2},
                                                                  {'total': Decimal('202.00'), 'id': 3}],
         'customer_name': u'Ron Weasley'},
        {'currency': u'RON', 'issue_date': '2017 Jul', 'values': [{'total': Decimal('303.00'), 'id': 4}],
         'customer_name': u'Ron Weasley'}
    ]


@pytest.mark.django_db
def test_stats_transaction_view_is_correct(api_client, create_transaction):
    url = reverse('transaction_stats')
    response = api_client.get(url, {'result_type': 'amount',
                                    'granulation_created_at': 'month',
                                    'granulation_customer': True})

    # granulation_list = [{'name': 'created_at', 'value': 'month'}, {'name': 'customer', 'value': None}]
    # stats = Stats(Transaction.objects.all(), 'amount', None, granulation_list)

    assert response.data == [
        {'currency': u'RON', 'created_at': '2017 Jul', 'values': [{'total': Decimal('20.00'), 'id': 3}],
         'customer_name': u'Hermione Granger'},
        {'currency': u'RON', 'created_at': '2017 Sep', 'values': [{'total': Decimal('10.00'), 'id': 1}],
         'customer_name': u'Hermione Granger'},
        {'currency': u'RON', 'created_at': '2017 Jul', 'values': [{'total': Decimal('15.00'), 'id': 2},
                                                                  {'total': Decimal('20.00'), 'id': 4}],
         'customer_name': u'Ron Weasley'}
    ]
