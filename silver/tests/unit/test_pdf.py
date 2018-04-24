import pytest
from django.template.loader import get_template
from mock import patch

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
def test_pdf_mark_as_dirty_min_value():
    # somehow inconsistent state
    pdf = PDF.objects.create(dirty=-1)

    pdf.mark_as_dirty()

    assert pdf.dirty == 1

    pdf.refresh_from_db()

    assert pdf.dirty == 1
