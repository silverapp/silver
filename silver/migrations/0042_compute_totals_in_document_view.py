# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from decimal import Decimal

from django.db import migrations, models


def compute_totals_for_documents(apps, schema_editor):
    db_alias = schema_editor.connection.alias

    Invoice = apps.get_model('silver', 'Invoice')
    Proforma = apps.get_model('silver', 'Proforma')

    for invoice in Invoice.objects.using(db_alias).exclude(state='draft'):
        invoice._total = sum([])
        invoice._total_in_transaction_currency = invoice.compute_total_in_transaction_currency()
        invoice.save()

    for proforma in Proforma.objects.using(db_alias).exclude(state='draft'):
        proforma._total = proforma.compute_total()
        proforma._total_in_transaction_currency = proforma.compute_total_in_transaction_currency()
        proforma.save()


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0041_auto_20170929_1045'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='_total',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=19, null=True),
        ),
        migrations.AddField(
            model_name='invoice',
            name='_total_in_transaction_currency',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=19, null=True),
        ),
        migrations.AddField(
            model_name='proforma',
            name='_total',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=19, null=True),
        ),
        migrations.AddField(
            model_name='proforma',
            name='_total_in_transaction_currency',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=19, null=True),
        ),
        migrations.AddField(
            model_name='Document',
            name='_total',
            field=models.DecimalField(max_digits=19, decimal_places=2,
                                      null=True, blank=True),
        ),
        migrations.AddField(
            model_name='Document',
            name='_total_in_transaction_currency',
            field=models.DecimalField(max_digits=19, decimal_places=2,
                                      null=True, blank=True),
        ),
        migrations.RunPython(compute_totals_for_documents,
                             migrations.RunPython.noop),
        migrations.RunSQL(
            sql="""
                DROP VIEW IF EXISTS silver_document;
                CREATE VIEW silver_document AS SELECT
                    'invoice' AS `kind`, id, series, number, issue_date, due_date,
                    paid_date, cancel_date, state, provider_id, customer_id,
                    proforma_id as related_document_id, archived_customer,
                    archived_provider, sales_tax_percent, sales_tax_name, currency, pdf_id,
                    transaction_currency, _total, _total_in_transaction_currency,
                    FROM silver_invoice
                UNION
                SELECT
                    'proforma' AS `kind`, id, series, number, issue_date, due_date,
                    paid_date, cancel_date, state, provider_id, customer_id,
                    NULL as related_document_id, archived_customer,
                    archived_provider, sales_tax_percent, sales_tax_name, currency, pdf_id,
                    transaction_currency, _total, _total_in_transaction_currency
                    FROM silver_proforma WHERE invoice_id is NULL
            """,
            reverse_sql="""
                DROP VIEW IF EXISTS silver_document;
                CREATE VIEW silver_document AS SELECT
                    'invoice' AS `kind`, id, series, number, issue_date, due_date,
                    paid_date, cancel_date, state, provider_id, customer_id,
                    proforma_id as related_document_id, archived_customer,
                    archived_provider, sales_tax_percent, sales_tax_name, currency, pdf_id,
                    transaction_currency
                    FROM silver_invoice
                UNION
                SELECT
                    'proforma' AS `kind`, id, series, number, issue_date, due_date,
                    paid_date, cancel_date, state, provider_id, customer_id,
                    NULL as related_document_id, archived_customer,
                    archived_provider, sales_tax_percent, sales_tax_name, currency, pdf_id,
                    transaction_currency
                    FROM silver_proforma WHERE invoice_id is NULL
            """),
    ]
