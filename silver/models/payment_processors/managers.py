import importlib
import traceback

from django.conf import settings


class PaymentProcessorManager(object):
    class DoesNotExist(Exception):
        pass

    @classmethod
    def get_class(cls, reference):
        try:
            data = settings.PAYMENT_PROCESSORS[reference]
        except KeyError:
            raise cls.DoesNotExist

        full_path = data['path']
        path, processor = full_path.rsplit('.', 1)

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
        return klass

    @classmethod
    def get_instance(cls, reference):
        try:
            data = settings.PAYMENT_PROCESSORS[reference]
        except KeyError:
            raise cls.DoesNotExist
        klass = cls.get_class(reference)

        instance = klass(**data.get('settings', {}))
        instance.reference = reference
        instance.display_name = data.get('display_name')

        return instance

    @classmethod
    def all(cls):
        return settings.PAYMENT_PROCESSORS.keys()

    @classmethod
    def all_instances(cls):
        return [cls.get_instance(processor_name) for processor_name in cls.all()]

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
    def get_choices(cls):
        return [
            (name, data.get('display_name', name))
            for name, data in settings.PAYMENT_PROCESSORS.items()
        ]
