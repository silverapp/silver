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
