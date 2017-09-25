from django.conf.urls import url

from stats.api.views import TransactionStats, DocumentStats, SubscriptionStats, ChartsView, \
    ChartsJsView

urlpatterns = [
    url('^stats/transactions/$', TransactionStats.as_view(), name='transaction_stats'),
    url('^stats/documents/$', DocumentStats.as_view(), name='document_stats'),
    url('^stats/subscriptions/$', SubscriptionStats.as_view(), name='subscription_stats'),
    url('^stats/subscriptions/chart/$', ChartsView.as_view(), name='chart_billboard'),
    url('^stats/subscriptions/chart/js/$', ChartsJsView.as_view(), name='chart_js'),
]
