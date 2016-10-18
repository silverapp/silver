# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from decimal import Decimal

from django.db import migrations, models
import django.core.validators
import django_fsm


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0010_auto_20160912_1517'),
    ]

    operations = [
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('amount', models.DecimalField(max_digits=8, decimal_places=2, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))])),
                ('due_date', models.DateField(default=None, null=True, blank=True)),
                ('status', django_fsm.FSMField(default=b'unpaid', max_length=8, choices=[(b'unpaid', 'Unpaid'), (b'pending', 'Pending'), (b'paid', 'Paid'), (b'canceled', 'Canceled')])),
                ('visible', models.BooleanField(default=True)),
                ('currency', models.CharField(default=b'USD', help_text=b'The currency used for billing.', max_length=4, choices=[('AED', 'UAE Dirham'), ('AFN', 'Afghani'), ('ALL', 'Lek'), ('AMD', 'Armenian Dram'), ('ANG', 'Netherlands Antillian Guilder'), ('AOA', 'Kwanza'), ('ARS', 'Argentine Peso'), ('AUD', 'Australian Dollar'), ('AWG', 'Aruban Guilder'), ('AZN', 'Azerbaijanian Manat'), ('BAM', 'Convertible Marks'), ('BBD', 'Barbados Dollar'), ('BDT', 'Taka'), ('BGN', 'Bulgarian Lev'), ('BHD', 'Bahraini Dinar'), ('BIF', 'Burundi Franc'), ('BMD', 'Bermudian Dollar'), ('BND', 'Brunei Dollar'), ('BOB', 'Boliviano'), ('BOV', 'Mvdol'), ('BRL', 'Brazilian Real'), ('BSD', 'Bahamian Dollar'), ('BTN', 'Ngultrum'), ('BWP', 'Pula'), ('BYR', 'Belarussian Ruble'), ('BZD', 'Belize Dollar'), ('CAD', 'Canadian Dollar'), ('CDF', 'Congolese Franc'), ('CHE', 'WIR Euro'), ('CHF', 'Swiss Franc'), ('CHW', 'WIR Franc'), ('CLF', 'Unidades de fomento'), ('CLP', 'Chilean Peso'), ('CNY', 'Yuan Renminbi'), ('COP', 'Colombian Peso'), ('COU', 'Unidad de Valor Real'), ('CRC', 'Costa Rican Colon'), ('CUP', 'Cuban Peso'), ('CVE', 'Cape Verde Escudo'), ('CYP', 'Cyprus Pound'), ('CZK', 'Czech Koruna'), ('DJF', 'Djibouti Franc'), ('DKK', 'Danish Krone'), ('DOP', 'Dominican Peso'), ('DZD', 'Algerian Dinar'), ('EEK', 'Kroon'), ('EGP', 'Egyptian Pound'), ('ERN', 'Nakfa'), ('ETB', 'Ethiopian Birr'), ('EUR', 'Euro'), ('FJD', 'Fiji Dollar'), ('FKP', 'Falkland Islands Pound'), ('GBP', 'Pound Sterling'), ('GEL', 'Lari'), ('GHS', 'Ghana Cedi'), ('GIP', 'Gibraltar Pound'), ('GMD', 'Dalasi'), ('GNF', 'Guinea Franc'), ('GTQ', 'Quetzal'), ('GYD', 'Guyana Dollar'), ('HKD', 'Hong Kong Dollar'), ('HNL', 'Lempira'), ('HRK', 'Croatian Kuna'), ('HTG', 'Gourde'), ('HUF', 'Forint'), ('IDR', 'Rupiah'), ('ILS', 'New Israeli Sheqel'), ('INR', 'Indian Rupee'), ('IQD', 'Iraqi Dinar'), ('IRR', 'Iranian Rial'), ('ISK', 'Iceland Krona'), ('JMD', 'Jamaican Dollar'), ('JOD', 'Jordanian Dinar'), ('JPY', 'Yen'), ('KES', 'Kenyan Shilling'), ('KGS', 'Som'), ('KHR', 'Riel'), ('KMF', 'Comoro Franc'), ('KPW', 'North Korean Won'), ('KRW', 'Won'), ('KWD', 'Kuwaiti Dinar'), ('KYD', 'Cayman Islands Dollar'), ('KZT', 'Tenge'), ('LAK', 'Kip'), ('LBP', 'Lebanese Pound'), ('LKR', 'Sri Lanka Rupee'), ('LRD', 'Liberian Dollar'), ('LSL', 'Loti'), ('LTL', 'Lithuanian Litas'), ('LVL', 'Latvian Lats'), ('LYD', 'Libyan Dinar'), ('MAD', 'Moroccan Dirham'), ('MDL', 'Moldovan Leu'), ('MGA', 'Malagasy Ariary'), ('MKD', 'Denar'), ('MMK', 'Kyat'), ('MNT', 'Tugrik'), ('MOP', 'Pataca'), ('MRO', 'Ouguiya'), ('MTL', 'Maltese Lira'), ('MUR', 'Mauritius Rupee'), ('MVR', 'Rufiyaa'), ('MWK', 'Kwacha'), ('MXN', 'Mexican Peso'), ('MXV', 'Mexican Unidad de Inversion (UDI)'), ('MYR', 'Malaysian Ringgit'), ('MZN', 'Metical'), ('NAD', 'Namibia Dollar'), ('NGN', 'Naira'), ('NIO', 'Cordoba Oro'), ('NOK', 'Norwegian Krone'), ('NPR', 'Nepalese Rupee'), ('NZD', 'New Zealand Dollar'), ('OMR', 'Rial Omani'), ('PAB', 'Balboa'), ('PEN', 'Nuevo Sol'), ('PGK', 'Kina'), ('PHP', 'Philippine Peso'), ('PKR', 'Pakistan Rupee'), ('PLN', 'Zloty'), ('PYG', 'Guarani'), ('QAR', 'Qatari Rial'), ('RON', 'New Leu'), ('RSD', 'Serbian Dinar'), ('RUB', 'Russian Ruble'), ('RWF', 'Rwanda Franc'), ('SAR', 'Saudi Riyal'), ('SBD', 'Solomon Islands Dollar'), ('SCR', 'Seychelles Rupee'), ('SDG', 'Sudanese Pound'), ('SEK', 'Swedish Krona'), ('SGD', 'Singapore Dollar'), ('SHP', 'Saint Helena Pound'), ('SLL', 'Leone'), ('SOS', 'Somali Shilling'), ('SRD', 'Surinam Dollar'), ('STD', 'Dobra'), ('SVC', 'El Salvador Colon'), ('SYP', 'Syrian Pound'), ('SZL', 'Lilangeni'), ('THB', 'Baht'), ('TJS', 'Somoni'), ('TMM', 'Manat'), ('TND', 'Tunisian Dinar'), ('TOP', "Pa'anga"), ('TRY', 'New Turkish Lira'), ('TTD', 'Trinidad and Tobago Dollar'), ('TWD', 'New Taiwan Dollar'), ('TZS', 'Tanzanian Shilling'), ('UAH', 'Hryvnia'), ('UGX', 'Uganda Shilling'), ('USD', 'US Dollar'), ('USN', 'US Dollar (Next day)'), ('USS', 'US Dollar (Same day)'), ('UYI', 'Uruguay Peso en Unidades Indexadas'), ('UYU', 'Peso Uruguayo'), ('UZS', 'Uzbekistan Sum'), ('VEF', 'Bolivar Fuerte'), ('VND', 'Dong'), ('VUV', 'Vatu'), ('WST', 'Tala'), ('XAF', 'CFA Franc BEAC'), ('XAG', 'Silver'), ('XAU', 'Gold'), ('XBA', 'European Composite Unit (EURCO)'), ('XBB', 'European Monetary Unit (E.M.U.-6)'), ('XBC', 'European Unit of Account 9 (E.U.A.-9)'), ('XBD', 'European Unit of Account 17 (E.U.A.-17)'), ('XCD', 'East Caribbean Dollar'), ('XDR', 'Special Drawing Rights'), ('XFO', 'Gold-Franc'), ('XFU', 'UIC-Franc'), ('XOF', 'CFA Franc BCEAO'), ('XPD', 'Palladium'), ('XPF', 'CFP Franc'), ('XPT', 'Platinum'), ('XTS', 'Code for testing purposes'), ('XXX', 'No currency'), ('YER', 'Yemeni Rial'), ('ZAR', 'Rand'), ('ZMK', 'Zambian Kwacha'), ('ZWD', 'Zimbabwe Dollar')])),
                ('currency_rate_date', models.DateField(null=True, blank=True)),
                ('customer', models.ForeignKey(to='silver.Customer')),
            ],
        ),
        migrations.AlterField(
            model_name='invoice',
            name='proforma',
            field=models.ForeignKey(related_name='related_invoice', blank=True, to='silver.Proforma', null=True),
        ),
        migrations.AlterField(
            model_name='proforma',
            name='invoice',
            field=models.ForeignKey(related_name='related_proforma', blank=True, to='silver.Invoice', null=True),
        ),
        migrations.AddField(
            model_name='payment',
            name='invoice',
            field=models.OneToOneField(related_name='invoice_payment', null=True, blank=True, to='silver.Invoice'),
        ),
        migrations.AddField(
            model_name='payment',
            name='proforma',
            field=models.OneToOneField(related_name='proforma_payment', null=True, blank=True, to='silver.Proforma'),
        ),
        migrations.AddField(
            model_name='payment',
            name='provider',
            field=models.ForeignKey(to='silver.Provider'),
        ),
    ]
