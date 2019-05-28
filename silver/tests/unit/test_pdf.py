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

import pytest

from mock import patch

from django.template.loader import get_template

from silver.models import PDF


@pytest.mark.django_db
def test_generate_pdf():
    pdf = PDF.objects.create(dirty=1)

    filename = 'filename'
    template = get_template('billing_documents/invoice_pdf.html')
    context = {'filename': filename}

    with patch('django.db.models.fields.files.FieldFile.save', autospec=True) as mock_pdf_save:
        pdf.generate(template=template, context=context)

    assert pdf.dirty == 0

    assert mock_pdf_save.call_count == 1

    call_args = mock_pdf_save.call_args[0]
    assert call_args[0] == pdf.pdf_file
    assert call_args[1] == filename
    assert call_args[3] is True

    # because of the way the dirty helper methods have been implemented, it's possible that the
    # object will no longer represent the DB state
    pdf.refresh_from_db()

    assert pdf.dirty == 0


@pytest.mark.django_db
def test_generate_pdf_without_upload():
    pdf = PDF.objects.create(dirty=1)

    pdf.generate(template=get_template('billing_documents/invoice_pdf.html'),
                 context={}, upload=False)

    assert pdf.dirty == 1

    # because of the way the dirty helper methods have been implemented, it's possible that the
    # object will no longer represent the DB state
    pdf.refresh_from_db()

    assert pdf.dirty == 1


@pytest.mark.django_db
def test_pdf_mark_as_clean_mimic_2_threads():
    pdf = PDF.objects.create(dirty=1)

    pdf.mark_as_clean()

    assert pdf.dirty == 0

    # A different thread uses the same PDF, but it's still dirty there
    pdf.dirty = 1

    pdf.mark_as_clean()

    pdf.refresh_from_db()

    # The value in DB should not be negative, because mark_as_dirty would not work properly then
    assert pdf.dirty == 0


@pytest.mark.django_db
def test_pdf_mark_as_clean_min_value():
    pdf = PDF.objects.create(dirty=0)
    pdf.mark_as_clean()

    # be sure that basic dirty/clean logic can't down dirty field below 0

    assert pdf.dirty == 0

    pdf.refresh_from_db()

    assert pdf.dirty == 0
