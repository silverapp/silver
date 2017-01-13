# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0021_auto_20170109_1159'),
    ]

    def forwards_func(apps, schema_editor):
        Customer = apps.get_model('silver', 'Customer')
        for customer in Customer.objects.all():
            try:
                customer.first_name, customer.last_name = customer.name.rsplit(" ", 1)
            except ValueError:
                customer.last_name = customer.name
            customer.save()

    def reverse_func(apps, schema_editor):
        Customer = apps.get_model('silver', 'Customer')
        for customer in Customer.objects.all():
            if customer.first_name:
                customer.name = "%s %s" % (customer.first_name, customer.last_name)
            else:
                customer.name = customer.last_name
            customer.save()

    operations = [
        migrations.AlterModelOptions(
            name='customer',
            options={'ordering': ['last_name', 'first_name', 'company']},
        ),
        migrations.AddField(
            model_name='customer',
            name='first_name',
            field=models.CharField(default='', help_text=b"The customer's first name.", max_length=128),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='customer',
            name='last_name',
            field=models.CharField(default='', help_text=b"The customer's last name.", max_length=128),
            preserve_default=False,
        ),
        migrations.AlterIndexTogether(
            name='customer',
            index_together=set([('first_name', 'last_name', 'company')]),
        ),

        migrations.RunPython(forwards_func, reverse_func),

        migrations.RemoveField(
            model_name='customer',
            name='name',
        ),
    ]
