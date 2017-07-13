# Copyright (c) 2017 Presslabs SRL
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
from django.core.exceptions import ValidationError
from mock import MagicMock, patch

from django.test import TestCase, override_settings
from silver.models import Transaction
from silver.tests.factories import (InvoiceFactory, PaymentMethodFactory,
                                    TransactionFactory, ProformaFactory, DocumentEntryFactory)
from silver.tests.fixtures import (TriggeredProcessor, PAYMENT_PROCESSORS,
                                   triggered_processor)


@override_settings(PAYMENT_PROCESSORS=PAYMENT_PROCESSORS)
class TestDocumentsTransactions(TestCase):
    def test_pay_documents_on_transaction_settle(self):
        transaction = TransactionFactory.create(
            state=Transaction.States.Pending
        )
        transaction.settle()
        transaction.save()

        proforma = transaction.proforma
        invoice = transaction.invoice

        self.assertEqual(proforma.state, proforma.STATES.PAID)
        self.assertEqual(invoice.state, invoice.STATES.PAID)

    # also refunding needs to be tested when implemented

    def test_transaction_creation_for_issued_documents(self):
        """
            The happy case.
        """
        invoice = InvoiceFactory.create()
        customer = invoice.customer

        PaymentMethodFactory.create(
            payment_processor=triggered_processor, customer=customer,
            canceled=False,
            verified=True,
        )

        invoice.issue()

        transactions = Transaction.objects.filter(
            invoice=invoice, proforma=invoice.proforma
        )
        self.assertEqual(len(transactions), 1)

    def test_no_transaction_creation_for_issued_documents_case_1(self):
        """
            The payment method is not recurring
        """
        invoice = InvoiceFactory.create()
        customer = invoice.customer
        PaymentMethodFactory.create(
            payment_processor=triggered_processor, customer=customer,
            canceled=False,
            verified=False
        )

        mock_execute = MagicMock()
        with patch.multiple(TriggeredProcessor, execute_transaction=mock_execute):
            invoice.issue()

            transactions = Transaction.objects.filter(
                invoice=invoice, proforma=invoice.proforma
            )
            self.assertEqual(len(transactions), 0)

    def test_no_transaction_creation_for_issued_documents_case2(self):
        """
            The payment method is not usable
        """
        invoice = InvoiceFactory.create()
        customer = invoice.customer
        PaymentMethodFactory.create(
            payment_processor=triggered_processor, customer=customer,
            canceled=False
        )

        mock_execute = MagicMock()
        with patch.multiple(TriggeredProcessor, execute_transaction=mock_execute):
            invoice.issue()

            transactions = Transaction.objects.filter(
                invoice=invoice, proforma=invoice.proforma
            )
            self.assertEqual(len(transactions), 0)

    def test_no_transaction_creation_for_issued_documents_case3(self):
        """
            There are 1 pending and 1 settled transactions that together cover the document amount.
        """
        entry = DocumentEntryFactory(quantity=1, unit_price=100)
        invoice = InvoiceFactory.create(invoice_entries=[entry])
        invoice.issue()

        customer = invoice.customer
        payment_method = PaymentMethodFactory.create(
            payment_processor=triggered_processor, customer=customer,
            canceled=False,
            verified=False,
        )

        TransactionFactory.create(invoice=invoice,
                                  payment_method=payment_method,
                                  amount=invoice.total_in_transaction_currency / 2,
                                  state=Transaction.States.Settled)

        TransactionFactory.create(invoice=invoice,
                                  payment_method=payment_method,
                                  amount=invoice.total_in_transaction_currency / 2,
                                  state=Transaction.States.Pending)

        mock_execute = MagicMock()
        with patch.multiple(TriggeredProcessor, execute_transaction=mock_execute):
            expected_exception = ValidationError
            expected_message = "{'__all__': [u'Amount is greater than the amount that should be " \
                               "charged in order to pay the billing document.']}"
            try:
                TransactionFactory.create(invoice=invoice,
                                          payment_method=payment_method,
                                          amount=1)

                self.fail('{} not raised.'.format(str(expected_exception)))
            except expected_exception as e:
                self.assertEqual(str(e), expected_message)

            transactions = Transaction.objects.filter(
                payment_method=payment_method, invoice=invoice,
            )
            self.assertEqual(len(transactions), 2)

            self.assertEqual(mock_execute.call_count, 0)

    def test_no_transaction_creation_at_invoice_creation_from_proforma(self):
        proforma = ProformaFactory.create(invoice=None)

        customer = proforma.customer
        PaymentMethodFactory.create(
            payment_processor=triggered_processor, customer=customer,
            canceled=False,
            verified=True,
        )

        proforma.issue()

        self.assertEqual(len(Transaction.objects.filter(proforma=proforma)),
                         1)

        invoice = proforma.create_invoice()

        self.assertEqual(len(Transaction.objects.filter(proforma=proforma)), 1)

        transaction = Transaction.objects.filter(proforma=proforma)[0]
        self.assertEqual(transaction.invoice, invoice)

    def test_no_transaction_creation_at_proforma_pay(self):
        proforma = ProformaFactory.create(invoice=None)

        customer = proforma.customer
        PaymentMethodFactory.create(
            payment_processor=triggered_processor, customer=customer,
            canceled=False,
            verified=True,
        )

        proforma.issue()
        proforma.pay()

        invoice = proforma.invoice

        self.assertEqual(len(Transaction.objects.filter(proforma=proforma)), 1)

        transaction = Transaction.objects.filter(proforma=proforma)[0]
        self.assertEqual(transaction.invoice, invoice)

    def test_no_transaction_settle_with_only_related_proforma(self):
        proforma = ProformaFactory.create(invoice=None)

        customer = proforma.customer
        PaymentMethodFactory.create(
            payment_processor=triggered_processor, customer=customer,
            canceled=False,
            verified=True,
        )

        proforma.issue()

        transaction = proforma.transactions[0]
        # here transaction.proforma is the same object as the proforma from the
        # DB due to the way transition callbacks and saves are called

        transaction.settle()
        transaction.save()

        self.assertEqual(proforma.state, proforma.STATES.PAID)

        invoice = proforma.invoice
        self.assertEqual(invoice.state, invoice.STATES.PAID)

        self.assertEqual(list(proforma.transactions),
                         list(invoice.transactions))

        self.assertEqual(len(proforma.transactions), 1)

    def test_transaction_invoice_on_transaction_settle(self):
        transaction = TransactionFactory.create(
            state=Transaction.States.Pending,
            invoice=None
        )

        # here transaction.proforma is an old version of itself
        # the actual proforma that is saved in db has a related invoice
        # so a refresh_from_db is needed
        # test_no_transaction_settle_with_only_related_proforma would be enough
        # if the transition callbacks would be handled in post_save

        transaction.settle()
        transaction.save()

        transaction.refresh_from_db()

        proforma = transaction.proforma
        invoice = transaction.invoice

        self.assertEqual(proforma.invoice, invoice)
