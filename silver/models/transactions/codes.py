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


FAIL_CODES = {
    'default': {
        'message': 'The transaction has failed.'
    },
    'insufficient_funds': {
        'message': 'Your payment method doesn\'t have sufficient funds.',
        'solve_message': 'Add more funds to your payment method or use another payment method.'
    },
    'expired_payment_method': {
        'message': 'Your payment method has expired.',
        'solve_message': 'Renew your payment method or use another one.'
    },
}

REFUND_CODES = {
    'default': {
        'message': 'The transaction has been refunded.'
    },
}

CANCEL_CODES = {
    'default': {
        'message': 'The transaction has been canceled.'
    }
}
