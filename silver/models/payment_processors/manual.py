from silver.views import GenericTransactionView
from silver.forms import GenericTransactionForm

from .base import PaymentProcessorBase
from .mixins import ManualProcessorMixin


class ManualProcessor(PaymentProcessorBase, ManualProcessorMixin):
    transaction_view_class = GenericTransactionView
    form_class = GenericTransactionForm

    @staticmethod
    def setup(data=None):
        pass
