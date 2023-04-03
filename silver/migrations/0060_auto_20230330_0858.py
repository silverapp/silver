# Generated by Django 3.1.14 on 2023-03-30 08:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0059_auto_20230307_0939'),
    ]

    operations = [
        migrations.AddField(
            model_name='bonus',
            name='document_entry_behavior',
            field=models.CharField(choices=[('apply_directly_to_target', 'Apply directly to target entries'), ('apply_separately_per_entry', 'Apply as separate entry, per entry')], default='apply_separately_per_entry', help_text='Defines how the discount will be shown in the billing documents.', max_length=32),
        ),
    ]
