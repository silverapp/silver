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


DEFAULT_FAIL_CODE = 'default'
FAIL_CODES = {
    DEFAULT_FAIL_CODE: {
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
    'expired_card': {
        'message': 'Your credit card has expired.',
        'solve_message': 'Renew your credit card or use another payment method.'
    },
    'invalid_payment_method': {
        'message': 'The provided payment method is not valid.',
        'solve_message': 'Make sure you entered your credentials correctly.'
    },
    'invalid_card': {
        'message': 'The provided credit card is not valid.',
        'solve_message': 'Make sure you entered your credentials correctly.'
    },
    'limit_exceeded': {
        'message': 'The attempted transaction exceeds the withdrawal limit of '
                   'the payment method.',
        'solve_message': 'Raise your payment method\'s limit or use another one.'
    },
    'transaction_declined': {
        'message': 'The tranasction has been declined by the payment processor.',
        'solve_message': 'Use another payment method or try again later.'
    },
    'transaction_declined_by_bank': {
        'message': 'Your bank has declined the transaction.',
        'solve_message': 'Contact your bank or try again later.'
    },
    'transaction_hard_declined': {
        'message': 'The tranasction has been declined by the payment processor.',
        'solve_message': 'Use another payment method.'
    },
    'transaction_hard_declined_by_bank': {
        'message': 'Your bank has declined the transaction.',
        'solve_message': 'Contact your bank or use another payment method.'
    }
}

DEFAULT_REFUND_CODE = 'default'
REFUND_CODES = {
    DEFAULT_REFUND_CODE: {
        'message': 'The transaction has been refunded.'
    },
}

DEFAULT_CANCEL_CODE = 'default'
CANCEL_CODES = {
    DEFAULT_CANCEL_CODE: {
        'message': 'The transaction has been canceled.'
    }
}
