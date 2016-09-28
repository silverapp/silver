from .generics import GenericPaymentProcessor, ManualProcessorMixin


class ManualProcessor(GenericPaymentProcessor, ManualProcessorMixin):
    name = "Manual"

    @staticmethod
    def setup(data=None):
        pass
