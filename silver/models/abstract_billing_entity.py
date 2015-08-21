import jsonfield
from django.db import models
from django.utils.text import slugify
from livefield.models import LiveModel
from international.models import countries


class AbstractBillingEntity(LiveModel):
    name = models.CharField(
        max_length=128,
        help_text='The name to be used for billing purposes.'
    )
    company = models.CharField(max_length=128, blank=True, null=True)
    email = models.EmailField(max_length=254, blank=True, null=True)
    address_1 = models.CharField(max_length=128)
    address_2 = models.CharField(max_length=128, blank=True, null=True)
    country = models.CharField(choices=countries, max_length=3)
    city = models.CharField(max_length=128)
    state = models.CharField(max_length=128, blank=True, null=True)
    zip_code = models.CharField(max_length=32, blank=True, null=True)
    extra = models.TextField(
        blank=True, null=True,
        help_text='Extra information to display on the invoice '
                  '(markdown formatted).'
    )
    meta = jsonfield.JSONField(blank=True, null=True)

    class Meta:
        abstract = True
        index_together = (('name', 'company'),)
        ordering = ['name', 'company']

    @property
    def billing_name(self):
        return self.company or self.name

    @property
    def slug(self):
        return slugify(self.billing_name)

    def address(self):
        return ", ".join(filter(None, [self.address_1, self.city, self.state,
                                       self.zip_code, self.country]))
    address.short_description = 'Address'

    def get_list_display_fields(self):
        field_names = ['company', 'email', 'address_1', 'city', 'country',
                       'zip_code']
        return [getattr(self, field, '') for field in field_names]

    def get_archivable_field_values(self):
        field_names = ['name', 'company', 'email', 'address_1', 'address_2',
                       'city', 'country', 'city', 'state', 'zip_code', 'extra',
                       'meta']
        return {field: getattr(self, field, '') for field in field_names}

    def __unicode__(self):
        return (u'%s (%s)' % (self.name, self.company) if self.company
                else self.name)
