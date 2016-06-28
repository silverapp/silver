from django.core import validators


validate_reference = validators.RegexValidator(
    regex=r'^[^,]*$',
    message=u'Reference must not contain commas.'
)
