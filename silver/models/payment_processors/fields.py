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

from django.db.models import CharField

from silver.models import PaymentProcessorManager

from .base import PaymentProcessorBase


class PaymentProcessorField(CharField):
    def __init__(self, choices=(), *args, **kwargs):
        super(PaymentProcessorField, self).__init__(choices=choices, *args, **kwargs)
        self.validators = [self._not_empty_string_validator]

    def _not_empty_string_validator(self, value):
        if value == '':
            raise self.ValidationError

    def get_internal_type(self):
        return "CharField"

    def from_db_value(self, value, expression, connection, context):
        return self.to_python(value)

    def to_python(self, value):
        if value is None or isinstance(value, PaymentProcessorBase):
            return value

        return PaymentProcessorManager.get_instance(value)

    def get_prep_value(self, value):
        if isinstance(value, PaymentProcessorBase):
            return value.reference

        return value

    def validate(self, value, model_instance):
        super(PaymentProcessorField, self).validate(value, model_instance)
