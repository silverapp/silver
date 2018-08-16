# Copyright (c) 2017 Pressinfra SRL
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

from itertools import chain

from django.core.management.base import BaseCommand

from silver.models import Invoice, Proforma


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Generates the billing documents (Invoices, Proformas).'

    def handle(self, *args, **options):
        for document in chain(Invoice.objects.filter(pdf__dirty__gt=0),
                              Proforma.objects.filter(pdf__dirty__gt=0)):
            try:
                document.generate_pdf()
            except:
                logger.exception('Encountered exception while generating PDF for document '
                                 'with id=%s.', document.id)
