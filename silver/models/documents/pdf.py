import uuid

from xhtml2pdf import pisa

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Model, FileField, TextField, UUIDField, PositiveIntegerField, F
from django.db.models.functions import Greatest
from django.http import HttpResponse
from django.utils.module_loading import import_string

from silver.utils.pdf import fetch_resources


def get_storage():
    storage_settings = getattr(settings, 'SILVER_DOCUMENT_STORAGE', None)
    if not storage_settings:
        return

    storage_class = import_string(storage_settings[0])
    return storage_class(*storage_settings[1], **storage_settings[2])


def get_upload_path(instance, filename):
    return instance.upload_path


class PDF(Model):
    uuid = UUIDField(default=uuid.uuid4, unique=True)
    pdf_file = FileField(null=True, blank=True, editable=False,
                         storage=get_storage(), upload_to=get_upload_path)
    dirty = PositiveIntegerField(default=0)
    upload_path = TextField(null=True, blank=True)

    @property
    def url(self):
        return self.pdf_file.url if self.pdf_file else None

    def generate(self, template, context, upload=True):
        pdf_file_object = HttpResponse(content_type='application/pdf')

        html = template.render(context)
        pisa.pisaDocument(src=html.encode("UTF-8"),
                          dest=pdf_file_object,
                          encoding='UTF-8',
                          link_callback=fetch_resources)

        if not pdf_file_object:
            return

        if upload:
            self.upload(pdf_file_object=pdf_file_object, filename=context['filename'])

        return pdf_file_object

    def upload(self, pdf_file_object, filename):
        # the PDF's upload_path attribute needs to be set before calling this method

        pdf_content = ContentFile(pdf_file_object)

        with transaction.atomic():
            self.pdf_file.save(filename, pdf_content, True)
            self.mark_as_clean()

    def mark_as_dirty(self):
        with transaction.atomic():
            PDF.objects.filter(id=self.id).update(dirty=Greatest(F('dirty') + 1, 1))
            self.refresh_from_db(fields=['dirty'])

    def mark_as_clean(self):
        with transaction.atomic():
            PDF.objects.filter(id=self.id).update(dirty=Greatest(F('dirty') - self.dirty, 0))
            self.refresh_from_db(fields=['dirty'])
