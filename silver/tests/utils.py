from functools import wraps

from silver.models import PaymentProcessorManager


def register_processor(processor_class, **data):
    def decorator(func):
        @wraps(func)
        def func_wrapper(*args, **kwargs):
            PaymentProcessorManager.register(processor_class, **data)
            result = func(*args, **kwargs)
            PaymentProcessorManager.unregister(processor_class)
            return result

        return func_wrapper
    return decorator