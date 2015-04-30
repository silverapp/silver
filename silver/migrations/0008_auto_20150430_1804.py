# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0007_auto_20150430_1549'),
    ]

    operations = [
        migrations.AlterField(
            model_name='documententry',
            name='quantity',
            field=models.DecimalField(max_digits=19, decimal_places=4, validators=[django.core.validators.MinValueValidator(0.0)]),
        ),
        migrations.AlterField(
            model_name='documententry',
            name='unit_price',
            field=models.DecimalField(max_digits=19, decimal_places=4),
        ),
        migrations.AlterField(
            model_name='meteredfeature',
            name='included_units',
            field=models.DecimalField(help_text=b'The number of included units per plan interval.', max_digits=19, decimal_places=4, validators=[django.core.validators.MinValueValidator(0.0)]),
        ),
        migrations.AlterField(
            model_name='meteredfeature',
            name='included_units_during_trial',
            field=models.DecimalField(decimal_places=4, validators=[django.core.validators.MinValueValidator(0.0)], max_digits=19, blank=True, help_text=b'The number of included units during the trial period.', null=True),
        ),
        migrations.AlterField(
            model_name='meteredfeature',
            name='price_per_unit',
            field=models.DecimalField(help_text=b'The price per unit.', max_digits=19, decimal_places=4, validators=[django.core.validators.MinValueValidator(0.0)]),
        ),
        migrations.AlterField(
            model_name='meteredfeatureunitslog',
            name='consumed_units',
            field=models.DecimalField(max_digits=19, decimal_places=4, validators=[django.core.validators.MinValueValidator(0.0)]),
        ),
        migrations.AlterField(
            model_name='plan',
            name='amount',
            field=models.DecimalField(help_text=b'The amount in the specified currency to be charged on the interval specified.', max_digits=19, decimal_places=4, validators=[django.core.validators.MinValueValidator(0.0)]),
        ),
    ]
