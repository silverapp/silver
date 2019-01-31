from decimal import Decimal

from django.utils import timezone
from django.utils.six import text_type

from silver.tests.api.specs.url import (
    spec_invoice_url, spec_customer_url, spec_provider_url, spec_proforma_url, spec_transaction_url,
    spec_transaction_pay_url, spec_payment_method_url)
from silver.tests.api.specs.utils import (
    ResourceDefinition, datetime_to_str, datetime_to_str_or_none
)

# required is True by default, (a default must be specified otherwise)
# read_only is False by default,
# write_only is False by default,
transaction_definition = ResourceDefinition("transaction", {
    'id': {
        'read_only': True,
        'output': lambda transaction: text_type(transaction.uuid),
    },
    'url': {
        'read_only': True,
        'output': lambda transaction: spec_transaction_url(transaction),
    },
    'customer': {
        'expected_input_types': text_type,
        'output': lambda transaction: spec_customer_url(transaction.customer),
        'assertions': [
            lambda input, transaction, output: input == output
        ]
    },
    'provider': {
        'expected_input_types': text_type,
        'output': lambda transaction: spec_provider_url(transaction.provider),
        'assertions': [
            lambda input, transaction, output: input == output
        ]
    },
    'currency': {
        'expected_input_types': text_type,
        'output': lambda transaction: transaction.currency,
    },
    'amount': {
        'required': False,
        'expected_input_types': (int, float, text_type),
        'output': lambda transaction: "%.2f" % Decimal(transaction.amount),
        'assertions': [
            lambda input, transaction, output: (
                input == output if input else
                True
            )
        ]
    },
    'state': {
        'read_only': True,
        'output': lambda transaction: text_type(transaction.state),
        'assertions': [
            lambda input, transaction, output: output in [
                'initial', 'pending', 'settled', 'failed', 'canceled', 'refunded'
            ]
        ]
    },
    'invoice': {
        'expected_input_types': text_type,
        'output': lambda transaction: (
            spec_invoice_url(transaction.invoice) if transaction.invoice else None
        ),
        'assertions': [
            lambda input, transaction, output:
            input == output if input else
            True
        ]
    },
    'proforma': {
        'expected_input_types': text_type,
        'output': lambda transaction: (
            spec_proforma_url(transaction.proforma) if transaction.proforma else None
        ),
        'assertions': [
            lambda input, transaction, output:
            input == output if input else
            True
        ]
    },
    'updated_at': {
        'read_only': True,
        'output': lambda transaction: datetime_to_str(transaction.updated_at)
    },
    'created_at': {
        'read_only': True,
        'output': lambda transaction: datetime_to_str(transaction.created_at)
    },
    'fail_code': {
        'read_only': True,
        'output': lambda transaction: transaction.fail_code
    },
    'refund_code': {
        'read_only': True,
        'output': lambda transaction: transaction.refund_code
    },
    'cancel_code': {
        'read_only': True,
        'output': lambda transaction: transaction.cancel_code
    },
    'valid_until': {
        'output': lambda transaction: datetime_to_str_or_none(transaction.valid_until)
    },
    'can_be_consumed': {
        'read_only': True,
        'output': lambda transaction: bool(transaction.can_be_consumed)
    },
    'pay_url': {
        'read_only': True,
        'output': lambda transaction: (
            None if (
                transaction.state != transaction.States.Initial or
                (transaction.valid_until and transaction.valid_until < timezone.now())
            ) else
            spec_transaction_pay_url(transaction)
        )
    },
    'payment_method': {
        'expected_input_types': text_type,
        'output': lambda transaction: spec_payment_method_url(transaction.payment_method),
        'assertions': [
            lambda input, transaction, output: input == output
        ]
    },
    'payment_processor': {
        'read_only': True,
        'output': lambda transaction: transaction.payment_processor
    }
})


def spec_transaction(transaction):
    return transaction_definition.generate(transaction)
