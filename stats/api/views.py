from django.shortcuts import render

try:
    from django.views import View
except ImportError:
    from django.views.generic import View

from rest_framework import generics, permissions, filters
from rest_framework.response import Response

from silver.api.filters import TransactionFilter, SubscriptionFilter, InvoiceFilter
from silver.models import Transaction, Subscription, Invoice
from stats.stats import Stats


class ChartsView(View):
    def get(self, request, *args, **argv):
        return render(request, 'charts.html', {})


class ChartsJsView(View):
    def get(self, request, *args, **argv):
        return render(request, 'charts_js.html', {})


class SubscriptionStats(generics.ListAPIView):
    queryset = Subscription.objects.all()
    permission_classes = (permissions.IsAuthenticated,)
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = SubscriptionFilter

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        granulations_list = []

        query_params = self.request.query_params
        result_type = query_params.get('result_type')
        modifier = query_params.get('modifier', None)

        if query_params.get('granulation_plan', None) is not None:
            granulations_list.append({'name': 'plan',
                                      'value': None})
        if query_params.get('granulation_customer', None) is not None:
            granulations_list.append({'name': 'customer',
                                      'value': None})

        stats = Stats(queryset, result_type, modifier, granulations_list)

        return Response(data=stats.validate())


class DocumentStats(generics.ListAPIView):
    queryset = Invoice.objects.all()
    permission_classes = (permissions.IsAuthenticated,)
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = InvoiceFilter

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        granulations_list = []

        query_params = self.request.query_params
        result_type = query_params.get('result_type')
        modifier = query_params.get('modifier', None)

        if query_params.get('granulation_issue_date', None) is not None:

            granulations_list.append({'name': 'issue_date',
                                      'value': query_params.get('granulation_issue_date')})
        if query_params.get('granulation_paid_date', None) is not None:
            granulations_list.append({'name': 'paid_date',
                                      'value': query_params.get('granulation_paid_date')})
        if query_params.get('granulation_customer', None) is not None:
            granulations_list.append({'name': 'customer',
                                      'value': None})

        stats = Stats(queryset, result_type, modifier, granulations_list)

        return Response(data=stats.validate())


class TransactionStats(generics.ListAPIView):
    queryset = Transaction.objects.all()
    permission_classes = (permissions.IsAuthenticated,)
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = TransactionFilter

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        granulations_list = []

        query_params = self.request.query_params
        result_type = query_params.get('result_type')
        modifier = query_params.get('modifier', None)

        if query_params.get('granulation_created_at', None) is not None:

            granulations_list.append({'name': 'created_at',
                                      'value': query_params.get('granulation_created_at')})
        if query_params.get('granulation_updated_at', None) is not None:
            granulations_list.append({'name': 'updated_at',
                                      'value': query_params.get('granulation_updated_at')})
        if query_params.get('granulation_customer', None) is not None:
            granulations_list.append({'name': 'customer',
                                      'value': None})

        stats = Stats(queryset, result_type, modifier, granulations_list)

        return Response(data=stats.validate())
