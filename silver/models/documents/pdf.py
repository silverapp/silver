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

from __future__ import absolute_import

import uuid
from io import BytesIO

from xhtml2pdf import pisa

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import (
    Model, FileField, TextField, UUIDField, PositiveIntegerField, F
)
from django.db.models.functions import Greatest
from django.http import HttpResponse
from django.utils.module_loading import import_string
from django.utils.encoding import force_bytes

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
        html = template.render(context)
        pdf_file_object = BytesIO()
        pisa.pisaDocument(
            src=html.encode("UTF-8"),
            dest=pdf_file_object,
            encoding='UTF-8',
            link_callback=fetch_resources
        )

        if not pdf_file_object:
            return

        if upload:
            self.upload(
                pdf_file_object=force_bytes(pdf_file_object),
                filename=context['filename']
            )
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
