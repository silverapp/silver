# Copyright (c) 2015 Presslabs SRL
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

import pytest

from mock import patch, call, MagicMock

from silver.tasks import generate_pdfs, generate_pdf
from silver.tests.factories import InvoiceFactory, ProformaFactory
from silver.utils.pdf import fetch_resources


@pytest.mark.django_db
def test_generate_pdfs_task(monkeypatch):
    issued_invoice = InvoiceFactory.create()
    issued_invoice.issue()

    paid_invoice = InvoiceFactory.create()
    paid_invoice.issue()
    paid_invoice.pay()

    canceled_invoice = InvoiceFactory.create()
    canceled_invoice.issue()
    canceled_invoice.cancel()

    issued_invoice_already_generated = InvoiceFactory.create()
    issued_invoice_already_generated.issue()
    issued_invoice_already_generated.pdf.dirty = False
    issued_invoice_already_generated.pdf.save()

    issued_proforma = ProformaFactory.create()
    issued_proforma.issue()

    issued_proforma_already_generated = ProformaFactory.create()
    issued_proforma_already_generated.issue()
    issued_proforma_already_generated.pdf.dirty = False
    issued_proforma_already_generated.pdf.save()

    documents_to_generate = [issued_invoice, canceled_invoice, paid_invoice,
                             issued_proforma]

    for document in documents_to_generate:
        assert document.pdf.dirty

    lock_mock = MagicMock()
    monkeypatch.setattr('silver.tasks.redis.lock', lock_mock)

    with patch('silver.tasks.group') as group_mock:
        generate_pdfs()

        assert group_mock.call_count


@pytest.mark.django_db
def test_generate_pdf_task(settings, tmpdir, monkeypatch):
    settings.MEDIA_ROOT = tmpdir.strpath

    invoice = InvoiceFactory.create()
    invoice.issue()

    assert invoice.pdf.dirty

    pisa_document_mock = MagicMock(return_value=MagicMock(err=False))

    monkeypatch.setattr('silver.models.documents.pdf.pisa.pisaDocument',
                        pisa_document_mock)

    generate_pdf(invoice.id, invoice.kind)

    # pdf needs to be refreshed as the invoice reference in the test is not the same with the one
    # in the task
    invoice.pdf.refresh_from_db()

    assert not invoice.pdf.dirty

    assert invoice.pdf.url == settings.MEDIA_URL + invoice.get_pdf_upload_path()

    assert pisa_document_mock.call_count == 1

    assert len(pisa_document_mock.mock_calls) == 1
