# Generated by Django 3.2.13 on 2022-07-20 07:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0056_auto_20220628_1159'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='discount',
            name='duration',
        ),
        migrations.AddField(
            model_name='discount',
            name='duration_count',
            field=models.IntegerField(blank=True, help_text='Indicate the duration for which the discount is available, after a subscription started. If not set, the duration is indefinite.', null=True),
        ),
        migrations.AddField(
            model_name='discount',
            name='duration_interval',
            field=models.CharField(blank=True, choices=[('billing_cycle', 'Billing Cycle'), ('day', 'Day'), ('week', 'Week'), ('month', 'Month'), ('year', 'Year')], max_length=16, null=True),
        ),
        migrations.AddField(
            model_name='plan',
            name='alternative_metered_features_interval',
            field=models.CharField(blank=True, choices=[('day', 'Day'), ('week', 'Week'), ('month', 'Month'), ('year', 'Year')], help_text="Optional frequency with which a subscription's metered features should be billed.", max_length=12, null=True),
        ),
        migrations.AddField(
            model_name='plan',
            name='alternative_metered_features_interval_count',
            field=models.PositiveIntegerField(blank=True, help_text="Optional number of intervals between each subscription's metered feature billing.", null=True),
        ),
        migrations.AlterField(
            model_name='plan',
            name='interval_count',
            field=models.PositiveIntegerField(help_text='The number of intervals between each subscription billing.'),
        ),
        migrations.AlterField(
            model_name='discount',
            name='customers',
            field=models.ManyToManyField(blank=True, related_name='discounts', to='silver.Customer'),
        ),
        migrations.AlterField(
            model_name='discount',
            name='plans',
            field=models.ManyToManyField(blank=True, related_name='discounts', to='silver.Plan'),
        ),
        migrations.AlterField(
            model_name='discount',
            name='subscriptions',
            field=models.ManyToManyField(blank=True, related_name='discounts', to='silver.Subscription'),
        ),
    ]
