# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import uuid
from itertools import chain

from django.db import migrations, models
import django.db.models.deletion

import silver.models.documents.pdf


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0035_auto_20170206_0941'),
    ]

    def move_pdf_from_documents_to_model(apps, schema_editor):
        db_alias = schema_editor.connection.alias

        Invoice = apps.get_model('silver', 'Invoice')
        Proforma = apps.get_model('silver', 'Proforma')
        PDF = apps.get_model('silver', 'PDF')

        for document in chain(
            Invoice.objects.using(db_alias).exclude(state='draft'),
            Proforma.objects.using(db_alias).exclude(state='draft'),
        ):
            pdf_object = PDF.objects.using(db_alias).create()
            pdf_object.pdf_file = document.pdf_old
            pdf_object.save(using=db_alias)

            document.pdf = pdf_object
            document.save(using=db_alias)

    def move_pdf_from_model_to_documents(apps, schema_editor):
        db_alias = schema_editor.connection.alias

        Invoice = apps.get_model('silver', 'Invoice')
        Proforma = apps.get_model('silver', 'Proforma')

        for document in chain(
            Invoice.objects.using(db_alias).exclude(state='draft'),
            Proforma.objects.using(db_alias).exclude(state='draft'),
        ):
            document.pdf_old = document.pdf.pdf_file
            document.save()

    operations = [
        migrations.CreateModel(
            name='PDF',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.UUIDField(default=uuid.uuid4, unique=True)),
                ('pdf_file', models.FileField(upload_to=silver.models.documents.pdf.get_upload_path, null=True, editable=False, blank=True)),
                ('dirty', models.BooleanField(default=False)),
                ('upload_path', models.TextField(null=True, blank=True)),
            ],
        ),
        migrations.RenameField(
            model_name='invoice',
            old_name='pdf',
            new_name='pdf_old'
        ),
        migrations.RenameField(
            model_name='proforma',
            old_name='pdf',
            new_name='pdf_old'
        ),

        migrations.AddField(
            model_name='invoice',
            name='pdf',
            field=models.ForeignKey(to='silver.PDF', null=True, on_delete=django.db.models.deletion.SET_NULL),
        ),
        migrations.AddField(
            model_name='proforma',
            name='pdf',
            field=models.ForeignKey(to='silver.PDF', null=True, on_delete=django.db.models.deletion.SET_NULL),
        ),

        migrations.RunPython(move_pdf_from_documents_to_model,
                             move_pdf_from_model_to_documents),

        migrations.RemoveField(
            model_name='invoice',
            name='pdf_old',
        ),
        migrations.RemoveField(
            model_name='proforma',
            name='pdf_old',
        ),
    ]
