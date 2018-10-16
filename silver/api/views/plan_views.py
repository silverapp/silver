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

from annoying.functions import get_object_or_None
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import generics, permissions, status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from silver.api.filters import PlanFilter
from silver.api.serializers.common import MeteredFeatureSerializer
from silver.api.serializers.plans_serializer import PlanSerializer
from silver.models import Plan, MeteredFeature


class PlanList(generics.ListCreateAPIView):

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = PlanSerializer
    queryset = Plan.objects.all().prefetch_related('metered_features')
    filter_backends = (DjangoFilterBackend,)
    filter_class = PlanFilter


class PlanDetail(generics.RetrieveDestroyAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = PlanSerializer
    model = Plan

    def get_object(self):
        pk = self.kwargs.get('pk', None)
        return get_object_or_404(Plan, pk=pk)

    def patch(self, request, *args, **kwargs):
        plan = get_object_or_404(Plan.objects, pk=self.kwargs.get('pk', None))
        name = request.data.get('name', None)
        generate_after = request.data.get('generate_after', None)
        plan.name = name or plan.name
        plan.generate_after = generate_after or plan.generate_after
        plan.save()
        return Response(PlanSerializer(plan, context={'request': request}).data,
                        status=status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        plan = get_object_or_404(Plan.objects, pk=self.kwargs.get('pk', None))
        plan.enabled = False
        plan.save()
        return Response({"deleted": not plan.enabled},
                        status=status.HTTP_200_OK)


class PlanMeteredFeatures(generics.ListAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = MeteredFeatureSerializer
    model = MeteredFeature

    def get_queryset(self):
        plan = get_object_or_None(Plan, pk=self.kwargs['pk'])
        return plan.metered_features.all() if plan else None
