import uuid

from django_xhtml2pdf.utils import generate_pdf_template_object

from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models import Model, BooleanField, FileField, TextField, UUIDField
from django.http import HttpResponse
from django.utils.module_loading import import_string


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
    dirty = BooleanField(default=False)
    upload_path = TextField(null=True, blank=True)

    @property
    def url(self):
        return self.pdf_file.url if self.pdf_file else None

    def generate(self, template, context, upload=True):
        pdf_file_object = HttpResponse(content_type='application/pdf')

        generate_pdf_template_object(template, pdf_file_object, context)

        if not pdf_file_object:
            return

        if upload:
            self.upload(pdf_file_object=pdf_file_object, filename=context['filename'])

        return pdf_file_object

    def upload(self, pdf_file_object, filename):
        # the PDF's upload_path attribute needs to be set before calling this method

        pdf_content = ContentFile(pdf_file_object)

        # delete old pdf version
        if self.pdf_file:
            self.pdf_file.delete()

        self.pdf_file.save(filename, pdf_content, True)
