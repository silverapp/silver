from rest_framework import generics, permissions, filters
from rest_framework.response import Response

from silver.api.filters import TransactionFilter, SubscriptionFilter
from silver.models import Transaction, Subscription
from stats.api.serializers import TransactionStatsSerializer
from stats.stats import Stats
from datetime import datetime, timedelta


class TransactionStats(generics.ListAPIView):
    queryset = Transaction.objects.all()
    permission_classes = (permissions.IsAuthenticated,)
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = TransactionFilter

    def list(self, request, *args, **kwargs):
        granulations_list = []

        query_params = self.request.query_params
        result_type = query_params.get('result_type')
        modifier = query_params.get('modifier', None)
        if query_params.get('granulations_issue_date', None) is not None:
            granulations_list.append({'name': 'created_at',
                                      'value': query_params.get('granulations_issue_date')})
        if query_params.get('granulations_currency', None) is not None:
            granulations_list.append({'name': 'currency'})

        stats = Stats(self.queryset, result_type, modifier, granulations_list)

        return Response(data=stats.get_result())

class SubscriptionStats(generics.ListAPIView):
    queryset = Subscription.objects.all()
    permission_classes = (permissions.IsAuthenticated,)
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = SubscriptionFilter

    def list(self, request, *args, **kwargs):
        query_params = self.request.query_params
        result_type = query_params.get('result_type')
        modifier = query_params.get('modifier', None)
        # start_date = query_params.get('start_date')
        # end_date = query_params.get('end_date')

        stats = Stats(self.queryset, result_type, modifier, {})

        return Response(data=stats.get_result())


