import importlib
import traceback

from django.db.models import CharField
from django.conf import settings

from .base import PaymentProcessorBase


class PaymentProcessorField(CharField):
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 256
        super(PaymentProcessorField, self).__init__(*args, **kwargs)
        self.validators = [self._not_empty_string_validator]

    def _not_empty_string_validator(self, value):
        if value == '':
            raise self.ValidationError

    def get_internal_type(self):
        return "CharField"

    def _from_string_value(self, value):
        path, processor = value.rsplit('.', 1)

        try:
            module = importlib.import_module(path)
            klass = getattr(module, processor, None)
        except Exception as e:
            traceback.print_exc()
            raise ImportError(
                "Couldn't import '{}' from '{}'\nReason: {}".format(processor, path, e)
            )
        if not klass:
            raise ImportError(
                "Couldn't import '{}' from '{}'".format(processor, path)
            )
        return klass()

    def _get_class_choice(self, klass):
        processors = [processor[0] for processor in settings.PAYMENT_PROCESSORS]
        for processor in processors:
            _klass = self._from_string_value(processor)
            if klass == _klass:
                return processor
        return None

    def from_db_value(self, value, expression, connection, context):
        return self.to_python(value)

    def to_python(self, value):
        if isinstance(value, PaymentProcessorBase):
            return value

        if value is None:
            return value

        return self._from_string_value(value)

    def get_prep_value(self, value):
        if not value:
            return value

        if isinstance(value, basestring):
            return value

        return self._get_class_choice(value)

    def validate(self, value, model_instance):
        value = self.get_prep_value(value)
        super(PaymentProcessorField, self).validate(value, model_instance)
