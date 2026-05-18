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

from decimal import Decimal

import jwt
from uuid import UUID

from django.apps import apps
from django.conf import settings
from django.http import Http404
from django.shortcuts import get_object_or_404


def get_transaction_from_token(view):
    def decorator(request, token):
        try:
            expired = False
            transaction_uuid = jwt.decode(token,
                                          settings.PAYMENT_METHOD_SECRET,
                                          algorithms=['HS256'])['transaction']
        except jwt.ExpiredSignatureError:
            expired = True
            transaction_uuid = jwt.decode(token, settings.PAYMENT_METHOD_SECRET,
                                          algorithms=['HS256'],
                                          options={'verify_exp': False})['transaction']

        try:
            uuid = UUID(transaction_uuid, version=4)
        except ValueError:
            raise Http404

        Transaction = apps.get_model('silver.Transaction')
        return view(request, get_object_or_404(Transaction, uuid=uuid), expired)
    return decorator


def require_transaction_xe_rate(f):
    def _check(self, *args, **kwargs):
        if not self.transaction_xe_rate:
            # This is a smelly hack :)
            if self.transaction_currency == self.currency:
                old_transaction_xe_rate = self.transaction_xe_rate

                self.transaction_xe_rate = Decimal(1)

                result = f(self, *args, **kwargs)

                self.transaction_xe_rate = old_transaction_xe_rate

                return result

            return None

        return f(self, *args, **kwargs)
    return _check
