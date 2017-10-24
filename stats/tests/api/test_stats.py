from decimal import Decimal

import pytest

try:
    from django.urls import reverse
except ImportError:
    from django.core.urlresolvers import reverse


@pytest.mark.django_db
def test_stats_billing_log_correct_url(api_client):
    assert reverse('billing_log_stats') == '/stats/billing_logs/'


@pytest.mark.django_db
def test_stats_documents_correct_url(api_client):
    assert reverse('document_stats') == '/stats/documents/'


@pytest.mark.django_db
def test_stats_transactions_correct_url(api_client):
    assert reverse('transaction_stats') == '/stats/transactions/'


@pytest.mark.django_db
def test_stats_billing_log_view_is_correct(api_client, create_subscription):
    url = reverse('billing_log_stats')
    response = api_client.get(url, {
        'result_type': 'total',
        'granulation_plan': True,
        'granulation_customer': True
    })

    assert response.data == [
        {
            'currency': u'USD',
            'values': [{
                'total': Decimal('20.00'),
                'billing_date': '01/31/2017',
                'id': 2
            }],
            'plan': u'Hydrogen',
            'customer_name': u'Harry Potter'
        },
        {
            'currency': u'RON',
            'values': [{
                'total': Decimal('10.00'),
                'billing_date': '01/11/2017',
                'id': 1
            }],
            'plan': u'Oxygen',
            'customer_name': u'Harry Potter'
        },
        {
            'currency': u'USD',
            'values': [{
                'total': Decimal('30.00'),
                'billing_date': '02/20/2017',
                'id': 4
            }],
            'plan': u'Enterprise',
            'customer_name': u'Ron Weasley'
        },
        {
            'currency': u'RON',
            'values': [
                {
                    'total': Decimal('20.00'),
                    'billing_date': '01/31/2017',
                    'id': 3
                },
                {
                    'total': Decimal('20.00'),
                    'billing_date': '01/31/2017', 'id': 3
                }
            ],
            'plan': u'Oxygen',
            'customer_name': u'Ron Weasley'
        }
    ]


@pytest.mark.django_db
def test_stats_document_view_is_correct(api_client, create_document):
    url = reverse('document_stats')
    response = api_client.get(url, {
        'result_type': 'amount',
        'granulation_issue_date': 'month',
        'granulation_customer': True
    })

    assert response.data == [
        {
            'currency': u'RON',
            'issue_date': 'Aug 2017',
            'values': [{
                'total': Decimal('101.00'),
                'id': 1}],
            'customer_name': u'Harry Potter'
        },
        {
            'currency': u'RON',
            'issue_date': 'Aug 2017',
            'values': [
                {
                    'total': 0,
                    'id': 2
                },
                {
                    'total': Decimal('202.00'),
                    'id': 3
                }
            ],
            'customer_name': u'Ron Weasley'
        },
        {
            'currency': u'RON',
            'issue_date': 'Jul 2017',
            'values': [{
                'total': Decimal('303.00'),
                'id': 4
            }],
            'customer_name': u'Ron Weasley'}
    ]


@pytest.mark.django_db
def test_stats_transaction_view_is_correct(api_client, create_transaction):
    url = reverse('transaction_stats')
    response = api_client.get(url, {
        'result_type': 'amount',
        'granulation_created_at': 'month',
        'granulation_customer': True
    })

    assert response.data == [
        {
            'currency': u'RON',
            'created_at': 'Jul 2017',
            'values': [{
                'total': Decimal('20.00'),
                'id': 3
            }],
            'customer_name': u'Hermione Granger'
        },
        {
            'currency': u'RON',
            'created_at': 'Sep 2017',
            'values': [{
                'total': Decimal('10.00'),
                'id': 1
            }],
            'customer_name': u'Hermione Granger'
        },
        {
            'currency': u'RON',
            'created_at': 'Jul 2017',
            'values': [
                {
                    'total': Decimal('15.00'),
                    'id': 2
                },
                {
                    'total': Decimal('20.00'),
                    'id': 4
                }
            ],
            'customer_name': u'Ron Weasley'
        }
    ]
