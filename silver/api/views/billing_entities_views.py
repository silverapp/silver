from django.http import Http404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, permissions
from rest_framework_bulk import ListBulkCreateAPIView

from silver.api.filters import CustomerFilter, ProviderFilter
from silver.api.serializers.billing_entities_serializers import CustomerSerializer, \
    ProviderSerializer
from silver.models import Customer, Provider


class CustomerList(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = CustomerSerializer
    queryset = Customer.objects.all()
    filter_backends = (DjangoFilterBackend,)
    filter_class = CustomerFilter


class CustomerDetail(generics.RetrieveUpdateDestroyAPIView):
    def get_object(self):
        pk = self.kwargs.get('customer_pk', None)
        try:
            return Customer.objects.get(pk=pk)
        except (TypeError, ValueError, Customer.DoesNotExist):
            raise Http404

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = CustomerSerializer
    model = Customer


class ProviderListCreate(ListBulkCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ProviderSerializer
    queryset = Provider.objects.all()
    filter_backends = (DjangoFilterBackend,)
    filter_class = ProviderFilter


class ProviderRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ProviderSerializer
    queryset = Provider.objects.all()
