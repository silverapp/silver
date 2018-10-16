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

from __future__ import absolute_import

import logging

from django.core.management.base import BaseCommand

from silver.models import Transaction, Invoice, Proforma
from silver.tests.factories import (TransactionFactory, InvoiceFactory, DocumentEntryFactory,
                                    ProformaFactory)


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Creating entities for testing purposes'

    def handle(self, *args, **options):
        proforma = ProformaFactory.create(proforma_entries=[DocumentEntryFactory.create()],
                                          state=Proforma.STATES.ISSUED)
        proforma.create_invoice()

        invoice = InvoiceFactory.create(invoice_entries=[DocumentEntryFactory.create()],
                                        state=Invoice.STATES.ISSUED,
                                        related_document=None)
        TransactionFactory.create(state=Transaction.States.Settled,
                                  invoice=invoice,
                                  payment_method__customer=invoice.customer,
                                  proforma=None)
        InvoiceFactory.create_batch(size=3,
                                    invoice_entries=[DocumentEntryFactory.create()],
                                    state=Invoice.STATES.PAID,
                                    related_document=None)
        InvoiceFactory.create_batch(size=3,
                                    invoice_entries=[DocumentEntryFactory.create()],
                                    state=Invoice.STATES.DRAFT,
                                    related_document=None)

        InvoiceFactory.create_batch(size=3,
                                    invoice_entries=[DocumentEntryFactory.create()],
                                    state=Invoice.STATES.CANCELED,
                                    related_document=None)
