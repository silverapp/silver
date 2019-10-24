from datetime import date
from decimal import Decimal

from django.utils.six import text_type

from silver.tests.api.specs.utils import ResourceDefinition


unaltered = lambda input_value: input_value
# required is True by default, (a default must be specified otherwise)
# read_only is False by default,
# write_only is False by default,
document_entry_definition = ResourceDefinition("document_entry", {
    'id': {
        'read_only': True,
        'output': lambda entry: int(entry.id),
    },
    'description': {
        'required': False,
        'expected_input_types': text_type,
        'output': lambda entry: entry.description
    },
    'unit': {
        'required': False,
        'expected_input_types': text_type,
        'output': lambda entry: entry.unit,
    },
    'unit_price': {
        'expected_input_types': (int, float, text_type),
        'output': lambda entry: "%.4f" % Decimal(entry.unit_price)
    },
    'quantity': {
        'expected_input_types': (int, float, text_type),
        'output': lambda entry: "%.4f" % Decimal(entry.quantity)
    },
    'total_before_tax': {
        'read_only': True,
        'output': lambda entry: "%.2f" % (entry.unit_price * entry.quantity)
    },
    'total': {
        'read_only': True,
        'output': lambda entry: "%.2f" % (
            entry.total_before_tax * Decimal(1 + entry.document.sales_tax_percent / 100)
        )
    },
    'start_date': {
        'required': False,
        'expected_input_types': date,
        'output': lambda entry: entry.start_date,
    },
    'end_date': {
        'required': False,
        'expected_input_types': date,
        'output': lambda entry: entry.end_date,
    },
    'prorated': {
        'required': False,
        'expected_input_types': bool,
        'output': lambda entry: entry.prorated,
    },
    'product_code': {
        'required': False,
        'expected_input_types': text_type,
        'output': lambda entry: entry.product_code,
    }
})


def spec_document_entry(entry):
    return document_entry_definition.generate(entry)
