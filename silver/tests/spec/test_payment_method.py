from rest_framework import permissions
from rest_framework.reverse import reverse

from silver.api.serializers import PaymentMethodSerializer
from silver.models import PaymentMethod
from silver.api.views import PaymentMethodList, PaymentMethodDetail
from silver.tests.factories import CustomerFactory, PaymentMethodFactory
from silver.tests.spec.util.api_get_assert import APIGetAssert


class TestPaymentMethodEndpoints(APIGetAssert):
    serializer_class = PaymentMethodSerializer

    def setUp(self):
        self.customer = CustomerFactory.create()

        super(TestPaymentMethodEndpoints, self).setUp()

    def create_payment_method(self, *args, **kwargs):
        method = PaymentMethodFactory.create(*args, **kwargs)

        # mysql does not store fractional time units but the object
        # created will have them so we can't use it directly
        #  to check the output
        method.refresh_from_db()

        return method

    def test_get_listing(self):
        PaymentMethodFactory.create(customer=CustomerFactory.create())
        method = self.create_payment_method(customer=self.customer)

        url = reverse('payment-method-list', kwargs={
            'customer_pk': self.customer.pk
        })

        self.assert_get_data(url, [method])

    def test_get_detail(self):
        PaymentMethodFactory.create(customer=CustomerFactory.create())
        method = self.create_payment_method(customer=self.customer)

        url = reverse('payment-method-detail', kwargs={
            'customer_pk': self.customer.pk,
            'payment_method_id': method.pk
        })

        self.assert_get_data(url, method)

    def test_post_listing(self):
        pass

    def test_put_patch_detail(self):
        pass

    def test_get_listing_no_customer(self):
        pass

    def test_get_detail_no_customer(self):
        pass

    def test_get_detail_no_payment_method(self):
        pass

    def test_post_listing_no_customer(self):
        pass

    def test_put_patch_detail_no_customer(self):
        pass

    def test_put_patch_detail_no_payment_method(self):
        pass

    def test_permissions(self):
        self.assertEqual(PaymentMethodList.permission_classes,
                         (permissions.IsAuthenticated,))
        self.assertEqual(PaymentMethodDetail.permission_classes,
                         (permissions.IsAuthenticated,))

    def test_filter_processor(self):
        method = self.create_payment_method(customer=self.customer)

        url = reverse('payment-method-list', kwargs={
            'customer_pk': self.customer.pk
        })

        url_manual_processor = url + '?processor=manual'
        url_no_output = url + '?processor=random'

        self.assert_get_data(url_manual_processor, [method])
        self.assert_get_data(url_no_output, [])

    def test_filter_state(self):
        method = self.create_payment_method(customer=self.customer,
                                            state=PaymentMethod.States.Enabled)

        url = reverse('payment-method-list', kwargs={
            'customer_pk': self.customer.pk
        })

        url_state_enabled = url + '?state=' + PaymentMethod.States.Enabled
        url_no_output = url + '?state=' + PaymentMethod.States.Disabled

        self.assert_get_data(url_state_enabled, [method])
        self.assert_get_data(url_no_output, [])
