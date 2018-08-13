from django.shortcuts import render

try:
    from django.views import View
except ImportError:
    from django.views.generic import View

from rest_framework import generics, permissions, filters
from rest_framework.response import Response

from silver.api.filters import TransactionFilter, InvoiceFilter, BillingLogFilter
from silver.models import Invoice, BillingLog, Transaction
from stats.stats import Stats


class ChartsView(View):
    def get(self, request, *args, **argv):
        return render(request, 'charts.html', {})


class ChartsJsView(View):
    def get(self, request, *args, **argv):
        return render(request, 'charts_js.html', {})


class BillingLogStats(generics.ListAPIView):
    queryset = BillingLog.objects.all()
    granulation_fields = ['granulation_plan', 'granulation_customer']
    permission_classes = (permissions.IsAuthenticated,)
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = BillingLogFilter

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        granulations = {}

        query_params = self.request.query_params
        result_type = query_params.get('result_type')
        modifier = query_params.get('modifier')

        for index, granulation in enumerate(self.granulation_fields):
            if query_params.get(granulation, None) is not None:
                if index == 0:
                    granulations['granulation_field'] = granulation[12:]
                else:
                    granulations['additional_granulation_field'] = granulation[12:]

        stats = Stats(queryset, result_type, modifier, granulations)

        return Response(data=stats.get_result())


class DocumentStats(generics.ListAPIView):
    queryset = Invoice.objects.all()
    granulation_fields = ['granulation_issue_date', 'granulation_paid_date', 'granulation_customer']
    permission_classes = (permissions.IsAuthenticated,)
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = InvoiceFilter

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        granulations = {}

        query_params = self.request.query_params
        result_type = query_params.get('result_type')
        modifier = query_params.get('modifier')

        for granulation in self.granulation_fields:
            if query_params.get(granulation, None) is not None:
                if query_params.get(granulation) == 'True':
                    granulations['additional_granulation_field'] = granulation[12:]
                else:
                    granulations['granulation_field'] = granulation[12:]
                    granulations['time_granulation_interval'] = query_params.get(granulation)

        stats = Stats(queryset, result_type, modifier, granulations)

        return Response(data=stats.get_result())


class TransactionStats(generics.ListAPIView):
    queryset = Transaction.objects.all()
    granulation_fields = ['granulation_created_at', 'granulation_paid_at', 'granulation_customer']
    permission_classes = (permissions.IsAuthenticated,)
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = TransactionFilter

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        granulations = {}

        query_params = self.request.query_params
        result_type = query_params.get('result_type')
        modifier = query_params.get('modifier')

        for granulation in self.granulation_fields:
            if query_params.get(granulation, None) is not None:
                if query_params.get(granulation) == 'True':
                    granulations['additional_granulation_field'] = granulation[12:]
                else:
                    granulations['granulation_field'] = granulation[12:]
                    granulations['time_granulation_interval'] = query_params.get(granulation)

        stats = Stats(queryset, result_type, modifier, granulations)

        return Response(data=stats.get_result())
