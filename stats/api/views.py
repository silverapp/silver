from django.shortcuts import render

try:
    from django.views import View
except ImportError:
    from django.views.generic import View

from rest_framework import generics, permissions, filters
from rest_framework.response import Response

from silver.api.filters import TransactionFilter, InvoiceFilter
from silver.models import Transaction, Invoice, BillingLog
from stats.stats import Stats


class ChartsView(View):
    def get(self, request, *args, **argv):
        return render(request, 'charts.html', {})


class ChartsJsView(View):
    def get(self, request, *args, **argv):
        return render(request, 'charts_js.html', {})


class BillingLogStats(generics.ListAPIView):
    queryset = BillingLog.objects.all()
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        granulations_list = []

        query_params = self.request.query_params
        result_type = query_params.get('result_type')
        modifier = query_params.get('modifier')

        for url_parameter, url_parameter_values in request.GET.lists():
            if url_parameter != 'result_type' and url_parameter != 'modifier':
                granulations_list.append({'name': url_parameter[12:],
                                          'value': url_parameter_values[0]})

        stats = Stats(queryset, result_type, modifier, granulations_list)

        return Response(data=stats.get_result())


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
        modifier = query_params.get('modifier')

        for url_parameter, url_parameter_values in request.GET.lists():
            if url_parameter != 'result_type' and url_parameter != 'modifier':
                granulations_list.append({'name': url_parameter[12:],
                                          'value': url_parameter_values[0]})

        stats = Stats(queryset, result_type, modifier, granulations_list)

        return Response(data=stats.get_result())


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
        modifier = query_params.get('modifier')

        for url_parameter, url_parameter_values in request.GET.lists():
            if url_parameter != 'result_type' and url_parameter != 'modifier':
                granulations_list.append({'name': url_parameter[12:],
                                          'value': url_parameter_values[0]})

        stats = Stats(queryset, result_type, modifier, granulations_list)

        return Response(data=stats.get_result())
