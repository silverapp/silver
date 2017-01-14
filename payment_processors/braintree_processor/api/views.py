# Copyright (c) 2017 Presslabs SRL
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

from annoying.functions import get_object_or_None
from payment_processors.braintree_processor import BraintreeTriggered
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from silver.models import Customer
from silver.models import Transaction


@api_view('GET')
def client_token(request, transaction_uuid=None):
    transaction = get_object_or_None(Transaction, id=transaction_uuid)

    if not isinstance(transaction.payment_processor, BraintreeTriggered):
        return Response(
            {'detail': 'Transaction is not a Braintree transaction.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    token = transaction.payment_processor.client_token(transaction.customer)

    if not token:
        return Response({'detail': 'Braintree miscommunication.'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response({'token': token}, status=status.HTTP_200_OK)
