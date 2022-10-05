from inspect import isclass

from django.contrib.admin.utils import model_format_dict
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.html import escape as html_escape
from django.utils.safestring import mark_safe


def get_admin_url(django_entity, anchored=True, safe=True, escape=True, text=None) -> str:
    """
    :param django_entity: Can be an instance of a model or a model class.
    :param anchored: Whether to wrap with html <a> tags.
    :param safe: Whether the content is considered html safe.
    :param escape: Whether the content needs to be html escaped.
    :param text: Optional text for the anchored URL.
    """
    obj = django_entity if not isclass(django_entity) else None
    klass = django_entity if not obj else obj.__class__

    if not text:
        if obj:
            text = obj.__str__()
        else:
            text = model_format_dict(django_entity)["verbose_name"]

    content_type = ContentType.objects.get_for_model(klass)

    if obj:
        url = reverse(
            f"admin:{content_type.app_label}_{content_type.model}_change",
            args=(obj.id,),
        )
    else:
        url = reverse(
            f"admin:{content_type.app_label}_{content_type.model}_changelist",
        )

    if escape:
        text = html_escape(text)

    if anchored:
        url = f"<a href={url}>{text}</a>"

    if safe:
        url = mark_safe(url)

    return url
