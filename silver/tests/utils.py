from functools import wraps

from silver.models import Transaction, PaymentProcessorManager
from silver.models.payment_processors.generics import (GenericPaymentProcessor,
                                                       TriggeredProcessorMixin)


def register_processor(processor_name='SomeProcessor'):
    def decorator(func):
        class SomeProcessor(GenericPaymentProcessor, TriggeredProcessorMixin):
            name = processor_name
            transaction_class = Transaction

            @staticmethod
            def setup(data=None):
                pass

        @wraps(func)
        def func_wrapper(*args, **kwargs):
            PaymentProcessorManager.register(SomeProcessor)
            result = func(*args, **kwargs)
            PaymentProcessorManager.unregister(SomeProcessor)
            return result

        return func_wrapper
    return decorator

