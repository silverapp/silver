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

from __future__ import absolute_import, unicode_literals

from annoying.fields import JSONField
from livefield import LiveModel

from django.conf import settings
from django.db import models
from django.utils.text import slugify
from django.utils.encoding import python_2_unicode_compatible

from silver.utils.international import countries


PAYMENT_DUE_DAYS = getattr(settings, 'SILVER_DEFAULT_DUE_DAYS', 5)


@python_2_unicode_compatible
class BaseBillingEntity(LiveModel):
    company = models.CharField(max_length=128, blank=True, null=True)
    address_1 = models.CharField(max_length=128)
    address_2 = models.CharField(max_length=128, blank=True, null=True)
    country = models.CharField(choices=countries, max_length=3)
    phone = models.CharField(max_length=32, blank=True, null=True)
    email = models.CharField(blank=True, null=True, max_length=254)
    city = models.CharField(max_length=128)
    state = models.CharField(max_length=128, blank=True, null=True)
    zip_code = models.CharField(max_length=32, blank=True, null=True)
    extra = models.TextField(
        blank=True, null=True,
        help_text='Extra information to display on the invoice '
                  '(markdown formatted).'
    )
    meta = JSONField(blank=True, null=True, default={})

    class Meta:
        abstract = True

    @property
    def billing_name(self):
        return self.company or self.name

    @property
    def slug(self):
        return slugify(self.billing_name)

    def address(self):
        return ", ".join([_f for _f in [
            self.address_1, self.city, self.state, self.zip_code, self.country] if _f
        ])
    address.short_description = 'Address'

    def get_list_display_fields(self):
        field_names = ['company', 'email', 'address_1', 'city', 'country',
                       'zip_code']
        return [getattr(self, field, '') for field in field_names]

    def get_archivable_field_values(self):
        field_names = ['company', 'email', 'address_1', 'address_2',
                       'city', 'country', 'city', 'state', 'zip_code', 'extra',
                       'meta']
        return {field: getattr(self, field, '') for field in field_names}

    def __str__(self):
        return (u'%s (%s)' % (self.name, self.company) if self.company
                else self.name)
