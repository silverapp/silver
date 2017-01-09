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

import traceback
from functools import wraps

from django.conf import settings


def ready(func):
    @wraps(func)
    def func_wrapper(cls, *args, **kwargs):
        if not cls._processors_registered:
            cls.register_processors()
        return func(cls, *args, **kwargs)
    return func_wrapper


class PaymentProcessorManager(object):
    _processors = {}

    _processors_registered = False

    class DoesNotExist(Exception):
        pass

    @classmethod
    def register(cls, processor_class, setup_data=None, display_name=None):
        setup_data = setup_data or {}
        if processor_class.reference not in cls._processors:
            cls._processors[processor_class.reference] = {
                'class': processor_class,
                'setup_data': setup_data,
                'display_name': display_name
            }

    @classmethod
    def unregister(cls, processor_class):
        reference = processor_class.reference
        if reference in cls._processors:
            del cls._processors[reference]

    @classmethod
    @ready
    def get_instance(cls, reference):
        try:
            processor = cls._processors[reference]
            processor_instance = processor['class'](**processor['setup_data'])

            if processor['display_name']:
                processor_instance.display_name = processor['display_name']

            return processor_instance
        except KeyError:
            raise cls.DoesNotExist

    @classmethod
    @ready
    def get_class(cls, reference):
        try:
            return cls._processors[reference]['class']
        except KeyError:
            raise cls.DoesNotExist

    @classmethod
    @ready
    def all_instances(cls):
        return [cls.get_instance(reference) for reference in cls._processors]

    @classmethod
    def register_processors(cls):
        for processor_path, data in settings.PAYMENT_PROCESSORS.items():
            path, processor = processor_path.rsplit('.', 1)

            try:
                processor_class = getattr(
                    __import__(path, globals(), locals(), [processor], 0),
                    processor
                )
            except Exception as e:
                traceback.print_exc()
                raise ImportError(
                    "Couldn't import '{}' from '{}'\nReason: {}".format(
                        processor,
                        path, e)
                )
            cls.register(processor_class,
                         data.get('setup_data'),
                         data.get('display_name'))

        cls._processors_registered = True

    @classmethod
    @ready
    def get_choices(cls):
        return [
            (processor['class'].reference,
             processor['display_name'] or processor['class'].display_name)
            for processor in cls._processors.values()
        ]
