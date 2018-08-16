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

from uuid import UUID

from django_filters.rest_framework import DjangoFilterBackend
from django_fsm import TransitionNotAllowed

from django.http import Http404

from rest_framework import permissions, status
from rest_framework.generics import ListCreateAPIView, get_object_or_404, RetrieveUpdateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from silver.api.filters import TransactionFilter
from silver.api.serializers.transaction_serializers import TransactionSerializer
from silver.models import PaymentMethod, Transaction


class TransactionList(ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = TransactionSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_class = TransactionFilter

    def get_queryset(self):
        customer_pk = self.kwargs.get('customer_pk', None)

        payment_method_id = self.kwargs.get('payment_method_id')
        if payment_method_id:
            payment_method = get_object_or_404(PaymentMethod,
                                               id=payment_method_id,
                                               customer__pk=customer_pk)

            return Transaction.objects.filter(
                payment_method=payment_method
            )
        else:
            return Transaction.objects.filter(
                payment_method__customer__pk=customer_pk
            )

    def perform_create(self, serializer):
        payment_method_id = self.kwargs.get('payment_method_id')
        if payment_method_id:
            payment_method = get_object_or_404(PaymentMethod,
                                               id=payment_method_id)
            serializer.save(payment_method=payment_method)
        else:
            serializer.save()


class TransactionDetail(RetrieveUpdateAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = TransactionSerializer
    http_method_names = ('get', 'patch', 'head', 'options')

    def get_object(self):
        transaction_uuid = self.kwargs.get('transaction_uuid', None)
        try:
            uuid = UUID(transaction_uuid, version=4)
        except ValueError:
            raise Http404

        return get_object_or_404(Transaction, uuid=uuid)


class TransactionAction(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    allowed_actions = ('cancel', )

    def post(self, request, *args, **kwargs):
        transaction = self.get_object(**kwargs)
        requested_action = kwargs.get('requested_action')

        if requested_action not in self.allowed_actions:
            error_message = "{} is not an allowed".format(requested_action)
            return Response({"errors": error_message},
                            status=status.HTTP_400_BAD_REQUEST)

        action_to_execute = getattr(transaction, requested_action, None)
        if not action_to_execute:
            raise Http404

        try:
            errors = action_to_execute()
            transaction.save()
        except TransitionNotAllowed:
            errors = "Can't execute action because the transaction is in an " \
                     "incorrect state: {}".format(transaction.state)

        if errors:
            return Response({"errors": errors},
                            status=status.HTTP_400_BAD_REQUEST)

        transaction_serialized = TransactionSerializer(transaction,
                                                       context={'request': request})
        return Response(transaction_serialized.data,
                        status=status.HTTP_200_OK)

    def get_object(self, **kwargs):
        transaction_uuid = kwargs.get('transaction_uuid')
        customer_pk = kwargs.get('customer_pk')

        return get_object_or_404(
            Transaction.objects.all(),
            uuid=transaction_uuid,
            payment_method__customer__pk=customer_pk
        )
