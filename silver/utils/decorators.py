# Copyright (c) 2016 Presslabs SRL
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

import jwt
from uuid import UUID

from django.conf import settings
from django.http import Http404
from django.shortcuts import get_object_or_404

from silver.models.transactions import Transaction


def get_transaction_from_token(view):
    def decorator(request, token):
        try:
            expired = False
            transaction_uuid = jwt.decode(token,
                                          settings.PAYMENT_METHOD_SECRET)['transaction']
        except jwt.ExpiredSignatureError:
            expired = True
            transaction_uuid = jwt.decode(token, settings.PAYMENT_METHOD_SECRET,
                                          options={'verify_exp': False})['transaction']

        try:
            uuid = UUID(transaction_uuid, version=4)
        except ValueError:
            raise Http404

        return view(request, get_object_or_404(Transaction, uuid=uuid), expired)
    return decorator
