from django.conf.urls import url

from stats.api.views import TransactionStats, SubscriptionStats, HomeView, SubscriptionStatsChart

urlpatterns = [
    url('^stats/transactions/$', TransactionStats.as_view(), name='transaction_parameters'),
    url('^stats/subscriptions/$', SubscriptionStats.as_view(), name='transaction_parameters'),
    url('^stats/subscriptions/chart/$', HomeView.as_view(), name='home'),
    url(r'^api/chart/data/$', SubscriptionStatsChart.as_view()),
]