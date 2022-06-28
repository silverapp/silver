from __future__ import absolute_import, unicode_literals

from django.template import TemplateDoesNotExist
from django.template.loader import get_template


def field_template_path(field, provider=None):
    if provider:
        provider_template_path = 'billing_documents/{provider}/{field}.html'.\
            format(provider=provider, field=field)
        try:
            get_template(provider_template_path)
            return provider_template_path
        except TemplateDoesNotExist:
            pass
    return 'billing_documents/{field}.html'.format(field=field)
