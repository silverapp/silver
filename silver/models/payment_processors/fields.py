from django.db.models import CharField
from django.utils.encoding import smart_text

from .managers import PaymentProcessorManager
from .generics import GenericPaymentProcessor


class PaymentProcessorField(CharField):
    def __init__(self, *args, **kwargs):
        max_length = 64
        kwargs['max_length'] = max_length
        super(PaymentProcessorField, self).__init__(*args, **kwargs)
        self.validators = []

    def get_internal_type(self):
        return "CharField"

    def from_string_value(self, value):
        return PaymentProcessorManager.get(name=value) or value

    def value_to_string(self, obj):
        return smart_text(obj) if obj else u''

    def from_db_value(self, value, *args, **kwargs):
        return self.to_python(value)

    def to_python(self, value):
        if isinstance(value, GenericPaymentProcessor):
            return value

        if value is None:
            return value

        return self.from_string_value(value)

    def get_prep_value(self, value):
        if not value:
            return value

        if isinstance(value, basestring):
            return value

        return value.name
