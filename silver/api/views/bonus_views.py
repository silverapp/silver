# Copyright (c) 2024 Pressinfra SRL
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

from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import generics, permissions

from silver.api.filters import BonusFilter
from silver.api.serializers.bonus_serializer import CustomerBonusSerializer
from silver.models import Bonus, Customer


class BonusList(generics.ListAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = CustomerBonusSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = BonusFilter

    def get_queryset(self):
        customer_pk = self.kwargs.get('customer_pk', None)
        queryset = Bonus.for_customer(Customer(pk=customer_pk))

        return queryset.order_by('start_date').distinct()
