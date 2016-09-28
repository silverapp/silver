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

    @classmethod
    def register(cls, processor, setup_data=None):
        name = processor.name.lower()
        if name not in cls.processors:
            processor.setup(setup_data)
            cls.processors[name] = processor()

    @classmethod
    @ready
    def get(cls, name):
        return cls.processors.get(name.lower())

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
            except Exception:
                traceback.print_exc()
                raise ImportError(
                    "Couldn't import '{}' from '{}'".format(processor, path)
                )

            cls.register(processor, setup_data)

        cls._processors_registered = True

    @classmethod
    @ready
    def get_choices(cls):
        return list(
            (processor, processor.name) for name, processor in
            cls.processors.items()  # if processor.state != 'disabled'
        )
