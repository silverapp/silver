from rest_framework.reverse import reverse

from silver.api.serializers import PaymentMethodSerializer
from silver.models import PaymentMethod
from silver.tests.factories import CustomerFactory, PaymentMethodFactory
from silver.tests.spec.util.api_get_assert import APIGetAssert


class TestPaymentMethodEndpoints(APIGetAssert):
    serializer_class = PaymentMethodSerializer

    def test_filter_processor(self):
        customer = CustomerFactory.create()
        payment_method = PaymentMethodFactory.create(
            customer=customer
        )

        # mysql does not store fractional time units but the object
        # created will have them so we can't use it directly
        #  to check the output
        payment_method.refresh_from_db()

        url = reverse('payment-method-list', kwargs={
            'customer_pk': customer.pk
        })

        url_manual_processor = url + '?processor=manual'
        url_no_output = url + '?processor=random'

        self.assert_get_data(url_manual_processor, [payment_method])
        self.assert_get_data(url_no_output, [])

    def test_filter_state(self):
        customer = CustomerFactory.create()
        payment_method_enabled = PaymentMethodFactory.create(
            customer=customer,
            state=PaymentMethod.States.Enabled,
        )
        payment_method_enabled.refresh_from_db()

        url = reverse('payment-method-list', kwargs={
            'customer_pk': customer.pk
        })

        url_state_enabled = url + '?state=' + PaymentMethod.States.Enabled
        url_no_output = url + '?state=' + PaymentMethod.States.Disabled

        self.assert_get_data(url_state_enabled, [payment_method_enabled])
        self.assert_get_data(url_no_output, [])
