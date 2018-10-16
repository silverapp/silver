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

from rest_framework import permissions, status
from rest_framework.generics import (ListAPIView, RetrieveAPIView, ListCreateAPIView,
                                     get_object_or_404, RetrieveUpdateAPIView)
from rest_framework.response import Response
from rest_framework.views import APIView

from silver import payment_processors
from silver.api.filters import PaymentMethodFilter
from silver.api.serializers.payment_methods_serializers import (PaymentProcessorSerializer,
                                                                PaymentMethodSerializer)
from silver.models import PaymentMethod, Customer


class PaymentProcessorList(ListAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = PaymentProcessorSerializer
    ordering = ('-name', )

    def get_queryset(self):
        return payment_processors.get_all_instances()


class PaymentProcessorDetail(RetrieveAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = PaymentProcessorSerializer
    ordering = ('-name', )

    def get_object(self):
        processor_name = self.kwargs.get('processor_name', '')
        try:
            return payment_processors.get_instance(processor_name)
        except (ImportError, KeyError):
            raise Http404


class PaymentMethodList(ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = PaymentMethodSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_class = PaymentMethodFilter

    def get_queryset(self):
        return PaymentMethod.objects.filter(customer=self.customer)

    def get_customer(self, request):
        context = self.get_parser_context(request)
        kwargs = context['kwargs']

        customer_pk = kwargs.get('customer_pk', None)

        return get_object_or_404(Customer, id=customer_pk)

    def list(self, request, *args, **kwargs):
        customer = self.get_customer(request)

        self.customer = customer

        return super(PaymentMethodList, self).list(request, *args, **kwargs)

    def perform_create(self, serializer):
        customer = self.get_customer(self.request)
        serializer.save(customer=customer)


class PaymentMethodDetail(RetrieveUpdateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = PaymentMethodSerializer

    def get_object(self):
        payment_method_id = self.kwargs.get('payment_method_id')
        customer_pk = self.kwargs.get('customer_pk')

        return get_object_or_404(
            PaymentMethod.objects.all().select_subclasses(),
            id=payment_method_id,
            customer__pk=customer_pk
        )


class PaymentMethodAction(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    allowed_actions = ('cancel', )

    def post(self, request, *args, **kwargs):
        payment_method = self.get_object(**kwargs)
        requested_action = kwargs.get('requested_action')

        if requested_action not in self.allowed_actions:
            error_message = "{} is not an allowed".format(requested_action)
            return Response({"errors": error_message},
                            status=status.HTTP_400_BAD_REQUEST)

        action_to_execute = getattr(payment_method, requested_action, None)

        if not action_to_execute:
            raise Http404

        errors = action_to_execute()
        if errors:
            return Response({"errors": errors},
                            status=status.HTTP_400_BAD_REQUEST)

        payment_method_serialized = PaymentMethodSerializer(payment_method,
                                                            context={'request': request})
        return Response(payment_method_serialized.data,
                        status=status.HTTP_200_OK)

    def get_object(self, **kwargs):
        payment_method_id = kwargs.get('payment_method_id')
        customer_pk = kwargs.get('customer_pk')

        return get_object_or_404(
            PaymentMethod.objects.all().select_subclasses(),
            id=payment_method_id,
            customer__pk=customer_pk
        )
