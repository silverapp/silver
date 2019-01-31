import inspect

from django.utils.six import text_type


datetime_to_str = lambda input_date: input_date.isoformat()[:-6] + 'Z'
datetime_to_str_or_none = lambda input_date: datetime_to_str(input_date) if input_date else None
date_to_str = lambda input_date: input_date.isoformat()
decimal_string_or_none = lambda input_decimal: (
    None if input_decimal is None else "%.2f" % input_decimal
)
text_type_or_none = lambda input: text_type(input) if input else None


class ResourceDefinition(object):
    def __init__(self, resource_name, field_definitions):
        # TODO: parse field definitions
        self.field_definitions = field_definitions
        self.field_defaults = {
            field: spec['default'] for field, spec in field_definitions.items()
            if 'default' in spec
        }
        self.field_assertions = {
            field: spec['assertions'] for field, spec in field_definitions.items()
            if 'assertions' in spec
        }
        self.resource_name = resource_name

    def generate(self, resource):
        representation = {}
        for field, field_spec in self.field_definitions.items():
            field_output = field_spec['output']

            if not field_spec.get('write_only', False):
                representation[field] = field_output(resource)

        return representation

    def check_response(self, resource, response_data, request_data=None):
        """Checks an endpoint response against the resource spec"""
        if request_data:
            self.check_request_input_types(request_data)
            self.check_request_input_output(resource, request_data, response_data)
            self.check_assertions(resource, request_data, response_data)

        # check overall output from DB object is according to spec
        assert response_data == self.generate(resource)

    def check_request_input_types(self, request_data):
        for field, value in request_data.items():
            field_spec = self.field_definitions[field]
            assert not field_spec.get('read_only'), (
                "Got read-only field '{field}' in request data.".format(field=field)
            )

            expected_input_types = field_spec['expected_input_types']
            if not field_spec.get('required', True):
                if value is None:
                    continue

            assert isinstance(value, expected_input_types), (
                "Expected request value < {value} > for field '{field}' to be one of "
                "{expected_input_types}. Actual type is {actual_type}.".format(
                    field=field, value=value, expected_input_types=expected_input_types,
                    actual_type=type(value)
                )
            )

    def check_request_input_output(self, resource, request_data, response_data):
        for field in request_data:
            field_definition = self.field_definitions[field]
            actual = response_data[field]

            expected = field_definition['output'](resource)

            assert actual == expected, (
                "Expected field '{field}' response value to be < {expected} >, but got "
                "< {actual} > instead.".format(field=field, actual=actual, expected=expected)
            )

    def check_assertions(self, resource, request_data, response_data):
        for field, assertions in self.field_assertions.items():
            field_spec = self.field_definitions[field]

            assertion_kwargs = {self.resource_name: resource}
            if not field_spec.get('read_only', False):
                # fix this to test requiredness maybe
                assertion_kwargs['input'] = request_data.get(field)
            if not field_spec.get('write_only', False):
                assertion_kwargs['output'] = response_data[field]

            for assertion in assertions:
                assert assertion(**assertion_kwargs), (
                    "Assertion failed for field {field}: \n{source}\n"
                    "input: {input}\n"
                    "{resource_name}: {resource}\n"
                    "output: {output}\n".format(
                        field=field, source=inspect.getsource(assertion),
                        resource_name=self.resource_name,
                        input=assertion_kwargs.get('input'),
                        resource=assertion_kwargs.get(self.resource_name),
                        output=assertion_kwargs.get('output'),
                    )
                )
