# Copyright (c) 2016 Presslabs SRL
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from datetime import date, timedelta

from django.test import TestCase

from silver.models import Payment
from silver.tests.factories import PaymentFactory


class TestPayment(TestCase):
    def test_payment_due_today_queryset(self):
        payments = PaymentFactory.create_batch(4)

        payments[0].due_date = date.today()
        payments[0].save()

        payments[1].status = Payment.Status.Pending
        payments[1].due_date = date.today()
        payments[1].save()

        payments[2].status = Payment.Status.Paid
        payments[2].due_date = date.today() - timedelta(days=1)
        payments[2].save()

        payments[3].status = Payment.Status.Canceled
        payments[3].due_date = date.today()
        payments[3].save()

        queryset = Payment.objects.due_today()

        assert queryset.count() == 2
        for payment in payments[0:1]:
            assert payment in queryset

    def test_payment_due_this_month_queryset(self):
        payments = PaymentFactory.create_batch(4)

        payments[0].due_date = date.today().replace(day=20)
        payments[0].save()

        payments[1].status = Payment.Status.Pending
        payments[1].due_date = date.today().replace(day=1)
        payments[1].save()

        payments[2].due_date = date.today() - timedelta(days=31)
        payments[2].save()

        payments[3].status = Payment.Status.Canceled
        payments[3].save()

        queryset = Payment.objects.due_this_month()

        assert queryset.count() == 2
        for payment in payments[0:1]:
            assert payment in queryset

    def test_payment_overdue_queryset(self):
        payments = PaymentFactory.create_batch(3)

        payments[0].due_date = date.today() - timedelta(days=1)
        payments[0].save()

        payments[1].status = Payment.Status.Pending
        payments[1].due_date = date.today() - timedelta(days=3)
        payments[1].save()

        payments[2].status = Payment.Status.Paid
        payments[2].due_date = date.today() - timedelta(days=31)
        payments[2].save()

        queryset = Payment.objects.overdue()

        assert queryset.count() == 2
        for payment in payments[0:1]:
            assert payment in queryset

    def test_payment_overdue_since_last_month_queryset(self):
        payments = PaymentFactory.create_batch(3)

        payments[0].due_date = date.today().replace(day=1)
        payments[0].save()

        payments[1].status = Payment.Status.Pending
        payments[1].due_date = date.today().replace(day=1)
        payments[1].save()

        payments[2].status = Payment.Status.Unpaid
        payments[2].due_date = date.today() - timedelta(days=31)
        payments[2].save()

        queryset = Payment.objects.overdue_since_last_month()

        assert queryset.count() == 1
        assert payments[2] in queryset
