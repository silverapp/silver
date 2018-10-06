# Copyright (c) 2015 Presslabs SRL
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import

from django.http import Http404
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import generics, permissions
from rest_framework_bulk import ListBulkCreateAPIView

from silver.api.filters import CustomerFilter, ProviderFilter
from silver.api.serializers.billing_entities_serializers import (
    CustomerSerializer, ProviderSerializer
)
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
