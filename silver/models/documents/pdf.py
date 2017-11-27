import uuid

import os
import pdfkit
import urlparse

import tempfile
from django.test import override_settings
from furl import furl
from xhtml2pdf import pisa

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Model, FileField, TextField, UUIDField, PositiveIntegerField, F
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

    def generate(self, html=None, template=None, context=None, upload=True):
        options = {
            'page-size': 'A4',
            'encoding': 'UTF-8',
        }
        options.update(getattr(settings, "SILVER_PDF_OPTIONS", {}))

        if html:
            pdf_file_object = pdfkit.from_string(html, False, options=options)
        else:
            static_url, media_url = settings.STATIC_URL, settings.MEDIA_URL
            if hasattr(settings, 'SITE_URL'):
                if not furl(settings.SITE_URL).scheme:
                    raise RuntimeError('settings.SITE_URL must contain a scheme.')

                static_url = furl(settings.SITE_URL).add(path=static_url).url
                media_url = furl(settings.SITE_URL).add(path=media_url).url

            try:
                with override_settings(STATIC_URL=static_url, MEDIA_URL=media_url), \
                        tempfile.NamedTemporaryFile(suffix='.html', delete=False) as header_html, \
                        tempfile.NamedTemporaryFile(suffix='.html', delete=False) as footer_html:
                    print(static_url, media_url)
                    context['render'] = 'content'
                    html = template.render(context)
                    print html, '=' * 20

                    context['render'] = 'header'
                    header_html.write(template.render(context).encode('utf-8'))
                    print template.render(context).encode('utf-8'), '=' * 20

                    context['render'] = 'footer'
                    footer_html.write(template.render(context).encode('utf-8'))
                    print template.render(context).encode('utf-8'), '=' * 20

                    options['margin-top'] = '50mm'
                    options['disable-smart-shrinking'] = ''
                    options['header-html'] = header_html.name
                    options['footer-html'] = footer_html.name

                    pdf_file_object = pdfkit.from_string(html, False, options=options)
            finally:
                # Ensure temporary header and footer files are deleted after rendering the PDF
                print(options['header-html'])
                os.remove(options['header-html'])
                os.remove(options['footer-html'])

        if not pdf_file_object:
            return

        if upload:
            self.upload(pdf_file_object=pdf_file_object, filename=context['filename'])

        self.mark_as_clean()

        return pdf_file_object

    def upload(self, pdf_file_object, filename):
        # the PDF's upload_path attribute needs to be set before calling this method

        pdf_content = ContentFile(pdf_file_object)

        self.pdf_file.save(filename, pdf_content, True)

    def mark_as_dirty(self):
        with transaction.atomic():
            PDF.objects.filter(id=self.id).update(dirty=F('dirty') + 1)
            self.refresh_from_db(fields=['dirty'])

    def mark_as_clean(self):
        PDF.objects.filter(id=self.id).update(dirty=F('dirty') - self.dirty)
