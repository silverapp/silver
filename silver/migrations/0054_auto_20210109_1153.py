# Generated by Django 3.1.5 on 2021-01-09 11:53

from django.db import migrations, models
import django_fsm


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0053_auto_20191028_1254'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transaction',
            name='fail_code',
            field=models.CharField(blank=True, choices=[('default', 'default'), ('insufficient_funds', 'insufficient_funds'), ('expired_payment_method', 'expired_payment_method'), ('expired_card', 'expired_card'), ('invalid_payment_method', 'invalid_payment_method'), ('invalid_card', 'invalid_card'), ('limit_exceeded', 'limit_exceeded'), ('transaction_declined', 'transaction_declined'), ('transaction_declined_by_bank', 'transaction_declined_by_bank'), ('transaction_hard_declined', 'transaction_hard_declined'), ('transaction_hard_declined_by_bank', 'transaction_hard_declined_by_bank')], max_length=64, null=True),
        ),
    ]