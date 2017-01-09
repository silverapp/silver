# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0018_auto_20170106_0921'),
    ]

    create_document_view = migrations.RunSQL("""
        DROP VIEW IF EXISTS silver_document;
        CREATE VIEW silver_document AS SELECT
            'invoice' AS `kind`, id, series, number, issue_date, due_date,
            paid_date, cancel_date, state, provider_id, customer_id,
            proforma_id as related_document_id, archived_customer,
            archived_provider, sales_tax_percent, sales_tax_name, currency, pdf
            FROM silver_invoice
        UNION
        SELECT
            'proforma' AS `kind`, id, series, number, issue_date, due_date,
            paid_date, cancel_date, state, provider_id, customer_id,
            NULL as related_document_id, archived_customer,
            archived_provider, sales_tax_percent, sales_tax_name, currency, pdf
            FROM silver_proforma WHERE invoice_id is NULL
    """)

    operations = [create_document_view, ]
