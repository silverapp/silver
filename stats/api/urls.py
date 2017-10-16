from django.conf.urls import url

from stats.api.views import TransactionStats, DocumentStats, ChartsView, \
    ChartsJsView, BillingLogStats

urlpatterns = [
    url('^stats/transactions/$', TransactionStats.as_view(), name='transaction_stats'),
    url('^stats/documents/$', DocumentStats.as_view(), name='document_stats'),
    url('^stats/billing_logs/$', BillingLogStats.as_view(), name='billing_log_stats'),
    url('^stats/subscriptions/chart/$', ChartsView.as_view(), name='chart_billboard'),
    url('^stats/subscriptions/chart/js/$', ChartsJsView.as_view(), name='chart_js'),
]
