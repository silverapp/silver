from datetime import date
from decimal import Decimal


from silver.tests.api.specs.utils import ResourceDefinition, date_to_str

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
        'expected_input_types': str,
        'output': lambda entry: entry.description
    },
    'unit': {
        'required': False,
        'expected_input_types': str,
        'output': lambda entry: entry.unit,
    },
    'unit_price': {
        'expected_input_types': (int, float, str),
        'output': lambda entry: "%.4f" % Decimal(entry.unit_price)
    },
    'quantity': {
        'expected_input_types': (int, float, str),
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
        'output': lambda entry: date_to_str(entry.start_date) if entry.start_date else None,
    },
    'end_date': {
        'required': False,
        'expected_input_types': date,
        'output': lambda entry: date_to_str(entry.end_date) if entry.end_date else None,
    },
    'prorated': {
        'required': False,
        'expected_input_types': bool,
        'output': lambda entry: entry.prorated,
    },
    'product_code': {
        'required': False,
        'expected_input_types': str,
        'output': lambda entry: str(entry.product_code) if entry.product_code else None,
    }
})


def spec_document_entry(entry):
    return document_entry_definition.generate(entry)
