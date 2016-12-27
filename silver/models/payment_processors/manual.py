from .base import PaymentProcessorBase
from .mixins import ManualProcessorMixin
from silver.views import GenericTransactionView


class ManualProcessor(PaymentProcessorBase, ManualProcessorMixin):
    view_class = GenericTransactionView

    @staticmethod
    def setup(data=None):
        pass
