from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.utils.six import text_type

from silver.tests.api.specs.customer import spec_archived_customer
from silver.tests.api.specs.document_entry import spec_document_entry, document_entry_definition
from silver.tests.api.specs.provider import spec_archived_provider
from silver.tests.api.specs.transaction import spec_transaction
from silver.tests.api.specs.url import spec_customer_url, spec_provider_url, spec_proforma_url
from silver.tests.api.specs.utils import date_to_str, decimal_string_or_none, ResourceDefinition
from silver.tests.api.utils.path import absolute_url

# required is True by default, (a default must be specified otherwise)
# read_only is False by default,
# write_only is False by default,
invoice_definition = ResourceDefinition("invoice", {
    'id': {
        'read_only': True,
        'output': lambda invoice: int(invoice.id),
    },
    'proforma': {
        'required': False,
        'expected_input_types': text_type,
        'output': lambda invoice: (
            spec_proforma_url(invoice.related_document) if invoice.related_document else None
        ),
        'assertions': [
            lambda input, invoice, output: (
                input == output if input else True
            )
        ]
    },
    'archived_provider': {
        'read_only': True,
        'output': lambda invoice: (
            {} if invoice.state == 'draft' else
            spec_archived_provider(invoice.provider)
        ),
    },
    'archived_customer': {
        'read_only': True,
        'output': lambda invoice: (
            {} if invoice.state == 'draft' else
            spec_archived_customer(invoice.customer)
        ),
    },
    'customer': {
        'expected_input_types': text_type,
        'output': lambda invoice: spec_customer_url(invoice.customer),
        'assertions': [
            lambda input, invoice, output: input == output
        ]
    },
    'provider': {
        'expected_input_types': text_type,
        'output': lambda invoice: spec_provider_url(invoice.provider),
        'assertions': [
            lambda input, invoice, output: input == output
        ]
    },
    'series': {
        'required': False,
        'expected_input_types': text_type,
        'output': lambda invoice: invoice.provider.invoice_series,
        'assertions': [
            lambda input, invoice, output: input == output if input else True
        ]
    },
    'number': {
        'required': False,
        'expected_input_types': int,
        'output': lambda invoice: invoice.number,
        'assertions': [
            lambda input, invoice, output: input == output if input else True
        ]
    },
    'currency': {
        'expected_input_types': text_type,
        'output': lambda invoice: invoice.currency,
        'assertions': [
            lambda input, invoice, output: input == output
        ]
    },
    'transaction_currency': {
        'required': False,
        'expected_input_types': text_type,
        'output': lambda invoice: invoice.transaction_currency or invoice.currency,
        'assertions': [
            lambda input, invoice, output: input == output if input else True
        ]
    },
    'transaction_xe_date': {
        'required': False,
        'expected_input_types': date,
        'output': lambda invoice: (
            None if invoice.state == 'draft' else
            None if invoice.currency == invoice.transaction_currency else
            date_to_str(invoice.issue_date - timedelta(days=1))
        ),
        'assertions': [
            lambda input, invoice, output: input == output if input else True
        ]
    },
    'transaction_xe_rate': {
        'required': False,
        'expected_input_types': (int, float, text_type),
        'output': lambda invoice: (
            "%.4f" % invoice.transaction_xe_rate if invoice.transaction_xe_rate else None
        ),
        'assertions': [
            lambda input, invoice, output: (
                "%.4f" % Decimal(input) == output if input else
                output is None if invoice.state == 'draft' else
                True  # transaction_xe_rate is based on transaction_xe_date
            )
        ]
    },
    'state': {
        'read_only': True,
        'output': lambda invoice: text_type(invoice.state),
        'assertions': [
            lambda output, **kw: output in ['draft', 'issued', 'canceled', 'paid']
        ]
    },
    'total': {
        'read_only': True,
        'output': lambda invoice: "%.2f" % (
            sum([entry.total for entry in invoice.entries])
        )
    },
    'total_in_transaction_currency': {
        'read_only': True,
        'output': lambda invoice: decimal_string_or_none(invoice.total_in_transaction_currency),
        'assertions': [
            lambda invoice, output: (
                output is None if not (
                    invoice.transaction_currency and (
                        invoice.transaction_xe_rate or
                        invoice.transaction_currency == invoice.currency
                    )
                ) else
                output == "%.2f" % (
                    sum([entry.total_in_transaction_currency for entry in invoice.entries])
                )
            )
        ]
    },
    'issue_date': {
        'required': False,
        'expected_input_types': date,
        'output': lambda invoice: (
            date_to_str(invoice.issue_date) if invoice.issue_date else None
        ),
        'assertions': [
            lambda input, invoice, output: (
                input == output if input else
                output is None if invoice.state == 'draft' else
                True
            )
        ]
    },
    'paid_date': {
        'required': False,
        'expected_input_types': date,
        'output': lambda invoice: (
            date_to_str(invoice.paid_date) if invoice.paid_date else None
        ),
        'assertions': [
            lambda input, invoice, output: (
                input == output if input else
                output is None if invoice.state != 'paid' else
                True
            )
        ]
    },
    'due_date': {
        'required': False,
        'expected_input_types': date,
        'output': lambda invoice: (
            date_to_str(invoice.due_date) if invoice.due_date else None
        ),
        'assertions': [
            lambda input, invoice, output: (
                input == output if input else
                output is None if invoice.state == 'draft' else
                output == date_to_str(invoice.issue_date + settings.SILVER_DEFAULT_DUE_DAYS)
            )
        ]
    },
    'cancel_date': {
        'required': False,
        'expected_input_types': date,
        'output': lambda invoice: (
            date_to_str(invoice.cancel_date) if invoice.cancel_date else None
        ),
        'assertions': [
            lambda input, invoice, output: (
                input == output if input else
                output is None if invoice.state != 'canceled' else
                True
            )
        ]
    },
    'sales_tax_percent': {
        'required': False,
        'expected_input_types': (int, float, text_type),
        'output': lambda invoice: "%.2f" % invoice.sales_tax_percent,
        'assertions': [
            lambda input, invoice, output: (
                "%.2f" % Decimal(input) == output if input else
                output == "%.2f" % invoice.customer.sales_tax_percent
            )
        ]
    },
    'sales_tax_name': {
        'required': False,
        'expected_input_types': text_type,
        'output': lambda invoice: invoice.sales_tax_name,
        'assertions': [
            lambda input, invoice, output: input == output if input else output == 'VAT'
        ]
    },
    'transactions': {
        'read_only': True,
        'output': lambda invoice: [
            spec_transaction(t) for t in invoice.transactions
        ]
    },
    'invoice_entries': {
        'required': False,
        'expected_input_types': list,
        'output': lambda invoice: [
            spec_document_entry(entry) for entry in invoice.entries
        ],
        'assertions': [
            lambda input, invoice, output: (
                len(input) == len(invoice.entries) == len(output) if input else
                len(invoice.entries) == len(output)
            ),
            # TODO
            # lambda input, invoice, output: (
            #     document_entry_definition.check_response(input, invoice.entries, output)
            # )
        ]
    },
    'pdf_url': {
        'read_only': True,
        'output': lambda invoice: (
            None if not (invoice.pdf and invoice.pdf.url) else
            absolute_url(invoice.pdf.url)
        )
    }
})


def spec_invoice(invoice):
    return invoice_definition.generate(invoice)
