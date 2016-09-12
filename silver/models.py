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


import datetime
from datetime import datetime as dt
from decimal import Decimal
import calendar
import logging

import jsonfield
import pycountry
from django_fsm import FSMField, transition, TransitionNotAllowed
from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
from django.core.files.base import ContentFile
from django.http import HttpResponse
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.utils.module_loading import import_string
from django.utils.text import slugify
from django_xhtml2pdf.utils import generate_pdf_template_object
from django.db import models
from django.db.models import Max
from django.conf import settings
from django.db.models.signals import pre_delete, pre_save
from django.dispatch.dispatcher import receiver
from django.core.validators import MinValueValidator
from django.template import TemplateDoesNotExist
from django.template.loader import (select_template, get_template,
                                    render_to_string)
from django.core.urlresolvers import reverse
from annoying.functions import get_object_or_None
from livefield.models import LiveModel
from dateutil import rrule
from pyvat import is_vat_number_format_valid
from model_utils import Choices

from silver.utils import next_month, prev_month
from silver.validators import validate_reference

countries = [ (country.alpha2, country.name) for country in pycountry.countries ]
currencies = [ (currency.letter, currency.name) for currency in pycountry.currencies ]

logger = logging.getLogger(__name__)


PAYMENT_DUE_DAYS = getattr(settings, 'SILVER_DEFAULT_DUE_DAYS', 5)
