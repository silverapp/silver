from django.conf.urls import url

from stats.api.views import TransactionStats, DocumentStats, SubscriptionStats, ChartsView

urlpatterns = [
    url('^stats/transactions/$', TransactionStats.as_view(), name='transaction_parameters'),
    url('^stats/documents/$', DocumentStats.as_view(), name='document_parameters'),
    url('^stats/subscriptions/$', SubscriptionStats.as_view(), name='subscription_parameters'),
    url('^stats/subscriptions/chart/$', ChartsView.as_view(), name='home'),
]
