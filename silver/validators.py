from django.core import validators
from django.core.exceptions import ValidationError

from silver.models.payment_processors import PaymentProcessorManager


validate_reference = validators.RegexValidator(
    regex=r'^[^,]*$',
    message=u'Reference must not contain commas.'
)


def validate_payment_processor(value):
    if value not in PaymentProcessorManager.all():
        raise ValidationError("{} is not a valid payment processor.".format(value))
