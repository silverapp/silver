# Generated by Django 3.2.16 on 2023-08-08 10:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0060_auto_20230330_0858'),
    ]

    operations = [
        migrations.AlterField(
            model_name='documententry',
            name='description',
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='description',
            field=models.TextField(blank=True, max_length=1024, null=True),
        ),
    ]
