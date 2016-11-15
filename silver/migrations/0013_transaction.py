# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0012_paymentmethod'),
    ]

    operations = [
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.UUIDField(default=uuid.uuid4)),
                ('valid_until', models.DateTimeField(null=True, blank=True)),
                ('last_access', models.DateTimeField(null=True, blank=True)),
                ('disabled', models.BooleanField(default=False)),
                ('payment', models.ForeignKey(to='silver.Payment')),
                ('payment_method', models.ForeignKey(to='silver.PaymentMethod')),
            ],
        ),
    ]
