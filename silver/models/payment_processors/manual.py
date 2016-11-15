from silver.views import GenericTransactionView

from .generics import GenericPaymentProcessor, ManualProcessorMixin


class ManualProcessor(GenericPaymentProcessor, ManualProcessorMixin):
    name = "Manual"
    view_class = GenericTransactionView

    @staticmethod
    def setup(data=None):
        pass
