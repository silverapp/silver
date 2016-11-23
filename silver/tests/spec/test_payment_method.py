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

        good_url = url + '?processor=manual'
        bad_url = url + '?processor=random'

        self.assert_get_data(good_url, [payment_method])
        self.assert_get_data(bad_url, [])

    def test_filter_state(self):
        customer = CustomerFactory.create()
        payment_method = PaymentMethodFactory.create(
            customer=customer,
            state=PaymentMethod.States.Enabled,
        )
        payment_method.refresh_from_db()

        url = reverse('payment-method-list', kwargs={
            'customer_pk': customer.pk
        })

        good_url = url + '?state=' + PaymentMethod.States.Enabled
        bad_url = url + '?state=' + PaymentMethod.States.Disabled

        self.assert_get_data(good_url, [payment_method])
        self.assert_get_data(bad_url, [])
