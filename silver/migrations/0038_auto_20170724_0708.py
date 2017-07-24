# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def change_pdf_dirty_from_boolean_to_integer(apps, schema_editor):
    db_alias = schema_editor.connection.alias

    PDF = apps.get_model('silver', 'PDF')
    for pdf in PDF.objects.using(db_alias).all():
        pdf.dirty = 1 if pdf.dirty_old else 0
        pdf.save(using=db_alias)


def change_pdf_dirty_from_integer_to_boolean(apps, schema_editor):
    db_alias = schema_editor.connection.alias

    PDF = apps.get_model('silver', 'PDF')
    for pdf in PDF.objects.using(db_alias).all():
        pdf.dirty_old = bool(pdf.dirty)
        pdf.save(using=db_alias)


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0037_auto_20170719_1159'),
    ]

    operations = [
        migrations.RenameField(
            model_name='pdf',
            old_name='dirty',
            new_name='dirty_old'
        ),
        migrations.AddField(
            model_name='pdf',
            name='dirty',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.RunPython(
            change_pdf_dirty_from_boolean_to_integer,
            change_pdf_dirty_from_integer_to_boolean
        ),
        migrations.RemoveField(
            model_name='pdf',
            name='dirty_old',
        ),
    ]
