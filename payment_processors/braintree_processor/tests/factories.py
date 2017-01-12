from payment_processors.braintree_processor import BraintreeTriggered
from silver.models import PaymentProcessorManager
from silver.tests.factories import TransactionFactory, PaymentMethodFactory


PaymentProcessorManager.register(BraintreeTriggered, display_name='Braintree')


class BraintreePaymentMethodFactory(PaymentMethodFactory):
    payment_processor = PaymentProcessorManager.get_instance(
        BraintreeTriggered.reference
    )


class BraintreeTransactionFactory(TransactionFactory):
    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        # overriding the payment_method field didn't work
        kwargs['payment_method'] = BraintreePaymentMethodFactory.create()

        return super(BraintreeTransactionFactory, cls)._create(
            model_class, *args, **kwargs
        )
