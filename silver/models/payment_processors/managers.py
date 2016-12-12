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
    processors = {}

    _processors_registered = False

    class DoesNotExist(Exception):
        pass

    @classmethod
    def register(cls, processor_class, setup_data=None):
        name = processor_class.name.lower()
        if name not in cls.processors:
            cls.processors[name] = processor_class()
            cls.processors[name].setup(setup_data)

    @classmethod
    def unregister(cls, processor_class):
        name = processor_class.name.lower()
        if name in cls.processors:
            del cls.processors[name]

    @classmethod
    @ready
    def get(cls, name):
        try:
            return cls.processors[name.lower()]
        except KeyError:
            raise cls.DoesNotExist

    @classmethod
    @ready
    def all(cls):
        return [value for key, value in cls.processors.items()]

    @classmethod
    def register_processors(cls):
        for processor_path, setup_data in settings.PAYMENT_PROCESSORS:
            path, processor = processor_path.rsplit('.', 1)
            try:
                processor = getattr(
                    __import__(path, globals(), locals(), [processor], 0),
                    processor
                )
            except Exception as e:
                traceback.print_exc()
                raise ImportError(
                    "Couldn't import '{}' from '{}'\nReason: {}".format(processor, path, e)
                )

            cls.register(processor, setup_data)

        cls._processors_registered = True

    @classmethod
    @ready
    def get_choices(cls):
        return list(
            (processor, processor.name) for name, processor in
            cls.processors.items()
        )
