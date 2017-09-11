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
    response = api_client.get(url, {'result_type': 'count',
                                    'granulations_issue_date': 'month',
                                    'granulations_currency': True})
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_stats_billing_correct_url(api_client):
    url = reverse('billing_stats')
    response = api_client.get(url, {'result_type': 'amount',
                                    'modifier': 'average',
                                    'granulations_issue_date': 'month',
                                    'granulations_currency': True})
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_stats_transactions_correct_url(api_client):
    url = reverse('transaction_stats')
    response = api_client.get(url, {'result_type': 'amount',
                                    'modifier': 'average',
                                    'granulations_issue_date': 'month',
                                    'granulations_currency': True})
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_stats_subscription_view_is_correct(api_client, create_subscription_and_billing_log):
    url = reverse('subscription_stats')
    response = api_client.get(url, {'result_type': 'estimated_income',
                                    'modifier': 'include_unused_plans'})
    stats = Stats(Subscription.objects.all(), 'estimated_income', 'include_unused_plans', [])
    print stats.validate()
    print response.data

    assert response.data == [
        {
            'granulations': {
                'plan': {'name': u'Oxygen', 'id': 3}},
            'values': [
                {'estimated_income': Decimal('500.00'), 'subscription_id': 3,
                 'customer_name': u'FirstN\xe1me2 LastN\xe1me2'},
                {'estimated_income': Decimal('400.00'), 'subscription_id': 2,
                 'customer_name': u'FirstN\xe1me1 LastN\xe1me1'},
                {'estimated_income': Decimal('300.00'), 'subscription_id': 1,
                 'customer_name': u'FirstN\xe1me0 LastN\xe1me0'}
            ]},
        {
            'granulations':
                {'plan': {'name': u'Hydrogen', 'id': 4}},
            'values': [
                {'estimated_income': Decimal('0.00'), 'subscription_id': 4,
                 'customer_name': u'FirstN\xe1me3 LastN\xe1me3'},
                {'estimated_income': Decimal('0.00'), 'subscription_id': 5,
                 'customer_name': u'FirstN\xe1me4 LastN\xe1me4'},
                {'estimated_income': Decimal('0.00'), 'subscription_id': 6,
                 'customer_name': u'FirstN\xe1me5 LastN\xe1me5'}
                ]}
    ]


@pytest.mark.django_db
def test_stats_document_view_is_correct(api_client, create_document):
    url = reverse('document_stats')
    response = api_client.get(url, {'result_type': 'count',
                                    'granulations_issue_date': 'month',
                                    'granulations_currency': True})

    assert response.data == [('1496275200', 'RON', 2), ('1498867200', 'RON', 2),
                             ('1501545600', 'RON', 1)]


@pytest.mark.django_db
def test_stats_billing_view_is_correct(api_client, create_subscription_and_billing_log):
    url = reverse('billing_stats')
    response = api_client.get(url, {'result_type': 'amount',
                                    'modifier': 'average',
                                    'granulations_issue_date': 'month',
                                    'granulations_currency': True})

    assert response.data == [('1498867200', Decimal('700.00')), ('1501545600', Decimal('450.00')),
                             ('1504224000', Decimal('300.00'))]


@pytest.mark.django_db
def test_stats_transaction_view_is_correct(api_client, create_transaction):
    url = reverse('transaction_stats')
    response = api_client.get(url, {'result_type': 'amount',
                                    'modifier': 'average',
                                    'granulations_issue_date': 'month',
                                    'granulations_currency': True})

    assert response.data == \
        [('1496275200', 'RON', Decimal('8321.00')), ('1498867200', 'RON', Decimal('6821.00')),
         ('1501545600', 'RON', Decimal('4821.00'))]
