# Copyright (c) 2015 Presslabs SRL
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django_fsm
import jsonfield.fields
import livefield.fields
import silver.models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='BillingLog',
            fields=[
                ('id', models.AutoField(verbose_name='ID',
                 serialize=False, auto_created=True, primary_key=True)),
                ('billing_date', models.DateField(
                    help_text=b'The date when the invoice/proforma was issued.')),
            ],
            options={
                'ordering': ['-billing_date'],
            },
        ),
        migrations.CreateModel(
            name='Customer',
            fields=[
                ('id', models.AutoField(verbose_name='ID',
                 serialize=False, auto_created=True, primary_key=True)),
                ('live', livefield.fields.LiveField(default=True)),
                ('name', models.CharField(
                    help_text=b'The name to be used for billing purposes.', max_length=128)),
                ('company', models.CharField(
                    max_length=128, null=True, blank=True)),
                ('email', models.EmailField(
                    max_length=254, null=True, blank=True)),
                ('address_1', models.CharField(max_length=128)),
                ('address_2', models.CharField(
                    max_length=128, null=True, blank=True)),
                ('country', models.CharField(max_length=3, choices=[('AF', 'Afghanistan'), ('AL', 'Albania'), ('AQ', 'Antarctica'), ('DZ', 'Algeria'), ('AS', 'American Samoa'), ('AD', 'Andorra'), ('AO', 'Angola'), ('AG', 'Antigua and Barbuda'), ('AZ', 'Azerbaijan'), ('AR', 'Argentina'), ('AU', 'Australia'), ('AT', 'Austria'), ('BS', 'Bahamas'), ('BH', 'Bahrain'), ('BD', 'Bangladesh'), ('AM', 'Armenia'), ('BB', 'Barbados'), ('BE', 'Belgium'), ('BM', 'Bermuda'), ('BT', 'Bhutan'), ('BO', 'Bolivia'), ('BA', 'Bosnia and Herzegovina'), ('BW', 'Botswana'), ('BV', 'Bouvet Island'), ('BR', 'Brazil'), ('BZ', 'Belize'), ('IO', 'British Indian Ocean Territory'), ('SB', 'Solomon Islands'), ('VG', 'British Virgin Islands'), ('BN', 'Brunei Darussalam'), ('BG', 'Bulgaria'), ('MM', 'Myanmar'), ('BI', 'Burundi'), ('BY', 'Belarus'), ('KH', 'Cambodia'), ('CM', 'Cameroon'), ('CA', 'Canada'), ('CV', 'Cape Verde'), ('KY', 'Cayman Islands'), ('CF', 'Central African Republic'), ('LK', 'Sri Lanka'), ('TD', 'Chad'), ('CL', 'Chile'), ('CN', 'China'), ('TW', 'Taiwan'), ('CX', 'Christmas Island'), ('CC', 'Cocos'), ('CO', 'Colombia'), ('KM', 'Comoros'), ('YT', 'Mayotte'), ('CG', 'Congo'), ('CD', 'Congo'), ('CK', 'Cook Islands'), ('CR', 'Costa Rica'), ('HR', 'Croatia'), ('CU', 'Cuba'), ('CY', 'Cyprus'), ('CZ', 'Czech Republic'), ('BJ', 'Benin'), ('DK', 'Denmark'), ('DM', 'Dominica'), ('DO', 'Dominican Republic'), ('EC', 'Ecuador'), ('SV', 'El Salvador'), ('GQ', 'Equatorial Guinea'), ('ET', 'Ethiopia'), ('ER', 'Eritrea'), ('EE', 'Estonia'), ('FO', 'Faroe Islands'), ('FK', 'Falkland Islands'), ('GS', 'South Georgia and the South Sandwich Islands'), ('FJ', 'Fiji'), ('FI', 'Finland'), ('AX', '\xc5land Islands'), ('FR', 'France'), ('GF', 'French Guiana'), ('PF', 'French Polynesia'), ('TF', 'French Southern Territories'), ('DJ', 'Djibouti'), ('GA', 'Gabon'), ('GE', 'Georgia'), ('GM', 'Gambia'), ('PS', 'Palestinian Territory'), ('DE', 'Germany'), ('GH', 'Ghana'), ('GI', 'Gibraltar'), ('KI', 'Kiribati'), ('GR', 'Greece'), ('GL', 'Greenland'), ('GD', 'Grenada'), ('GP', 'Guadeloupe'), ('GU', 'Guam'), ('GT', 'Guatemala'), ('GN', 'Guinea'), ('GY', 'Guyana'), ('HT', 'Haiti'), ('HM', 'Heard Island and McDonald Islands'), ('VA', 'Holy See'), ('HN', 'Honduras'), ('HK', 'Hong Kong'), ('HU', 'Hungary'), ('IS', 'Iceland'), ('IN', 'India'), ('ID', 'Indonesia'), ('IR', 'Iran'), ('IQ', 'Iraq'), ('IE', 'Ireland'), ('IL', 'Israel'), ('IT', 'Italy'), ('CI', "Cote d'Ivoire"), ('JM', 'Jamaica'), ('JP', 'Japan'), ('KZ', 'Kazakhstan'), ('JO', 'Jordan'), ('KE', 'Kenya'), ('KP', 'Korea'), ('KR', 'Korea'), ('KW', 'Kuwait'), ('KG', 'Kyrgyz Republic'), ('LA', "Lao People's Democratic Republic"), ('LB', 'Lebanon'), ('LS', 'Lesotho'), ('LV', 'Latvia'), ('LR', 'Liberia'), ('LY', 'Libyan Arab Jamahiriya'), ('LI', 'Liechtenstein'), ('LT', 'Lithuania'), ('LU', 'Luxembourg'), ('MO', 'Macao'), (
                    'MG', 'Madagascar'), ('MW', 'Malawi'), ('MY', 'Malaysia'), ('MV', 'Maldives'), ('ML', 'Mali'), ('MT', 'Malta'), ('MQ', 'Martinique'), ('MR', 'Mauritania'), ('MU', 'Mauritius'), ('MX', 'Mexico'), ('MC', 'Monaco'), ('MN', 'Mongolia'), ('MD', 'Moldova'), ('ME', 'Montenegro'), ('MS', 'Montserrat'), ('MA', 'Morocco'), ('MZ', 'Mozambique'), ('OM', 'Oman'), ('NA', 'Namibia'), ('NR', 'Nauru'), ('NP', 'Nepal'), ('NL', 'Netherlands'), ('AN', 'Netherlands Antilles'), ('CW', 'Cura\xe7ao'), ('AW', 'Aruba'), ('SX', 'Sint Maarten'), ('BQ', 'Bonaire'), ('NC', 'New Caledonia'), ('VU', 'Vanuatu'), ('NZ', 'New Zealand'), ('NI', 'Nicaragua'), ('NE', 'Niger'), ('NG', 'Nigeria'), ('NU', 'Niue'), ('NF', 'Norfolk Island'), ('NO', 'Norway'), ('MP', 'Northern Mariana Islands'), ('UM', 'United States Minor Outlying Islands'), ('FM', 'Micronesia'), ('MH', 'Marshall Islands'), ('PW', 'Palau'), ('PK', 'Pakistan'), ('PA', 'Panama'), ('PG', 'Papua New Guinea'), ('PY', 'Paraguay'), ('PE', 'Peru'), ('PH', 'Philippines'), ('PN', 'Pitcairn Islands'), ('PL', 'Poland'), ('PT', 'Portugal'), ('GW', 'Guinea-Bissau'), ('TL', 'Timor-Leste'), ('PR', 'Puerto Rico'), ('QA', 'Qatar'), ('RE', 'Reunion'), ('RO', 'Romania'), ('RU', 'Russian Federation'), ('RW', 'Rwanda'), ('BL', 'Saint Barthelemy'), ('SH', 'Saint Helena'), ('KN', 'Saint Kitts and Nevis'), ('AI', 'Anguilla'), ('LC', 'Saint Lucia'), ('MF', 'Saint Martin'), ('PM', 'Saint Pierre and Miquelon'), ('VC', 'Saint Vincent and the Grenadines'), ('SM', 'San Marino'), ('ST', 'Sao Tome and Principe'), ('SA', 'Saudi Arabia'), ('SN', 'Senegal'), ('RS', 'Serbia'), ('SC', 'Seychelles'), ('SL', 'Sierra Leone'), ('SG', 'Singapore'), ('SK', 'Slovakia'), ('VN', 'Vietnam'), ('SI', 'Slovenia'), ('SO', 'Somalia'), ('ZA', 'South Africa'), ('ZW', 'Zimbabwe'), ('ES', 'Spain'), ('SS', 'South Sudan'), ('EH', 'Western Sahara'), ('SD', 'Sudan'), ('SR', 'Suriname'), ('SJ', 'Svalbard & Jan Mayen Islands'), ('SZ', 'Swaziland'), ('SE', 'Sweden'), ('CH', 'Switzerland'), ('SY', 'Syrian Arab Republic'), ('TJ', 'Tajikistan'), ('TH', 'Thailand'), ('TG', 'Togo'), ('TK', 'Tokelau'), ('TO', 'Tonga'), ('TT', 'Trinidad and Tobago'), ('AE', 'United Arab Emirates'), ('TN', 'Tunisia'), ('TR', 'Turkey'), ('TM', 'Turkmenistan'), ('TC', 'Turks and Caicos Islands'), ('TV', 'Tuvalu'), ('UG', 'Uganda'), ('UA', 'Ukraine'), ('MK', 'Macedonia'), ('EG', 'Egypt'), ('GB', 'United Kingdom'), ('GG', 'Guernsey'), ('JE', 'Jersey'), ('IM', 'Isle of Man'), ('TZ', 'Tanzania'), ('US', 'United States'), ('VI', 'United States Virgin Islands'), ('BF', 'Burkina Faso'), ('UY', 'Uruguay'), ('UZ', 'Uzbekistan'), ('VE', 'Venezuela'), ('WF', 'Wallis and Futuna'), ('WS', 'Samoa'), ('YE', 'Yemen'), ('ZM', 'Zambia'), ('XX', 'Disputed Territory'), ('XE', 'Iraq-Saudi Arabia Neutral Zone'), ('XD', 'United Nations Neutral Zone'), ('XS', 'Spratly Islands'), ('XS', 'Spratly Islands')])),
                ('city', models.CharField(max_length=128)),
                ('state', models.CharField(
                    max_length=128, null=True, blank=True)),
                ('zip_code', models.CharField(
                    max_length=32, null=True, blank=True)),
                ('extra', models.TextField(
                    help_text=b'Extra information to display on the invoice (markdown formatted).', null=True, blank=True)),
                ('payment_due_days', models.PositiveIntegerField(
                    default=5, help_text=b'Due days for generated proforma/invoice.')),
                ('consolidated_billing', models.BooleanField(
                    default=False, help_text=b'A flag indicating consolidated billing.')),
                ('customer_reference', models.CharField(
                    help_text=b"It's a reference to be passed between silver and clients. It usually points to an account ID.", max_length=256, null=True, blank=True)),
                ('sales_tax_number', models.CharField(
                    max_length=64, null=True, blank=True)),
                ('sales_tax_percent', models.DecimalField(decimal_places=2, validators=[django.core.validators.MinValueValidator(
                    0.0)], max_digits=4, blank=True, help_text=b"Whenever to add sales tax. If null, it won't show up on the invoice.", null=True)),
                ('sales_tax_name', models.CharField(
                    help_text=b"Sales tax name (eg. 'sales tax' or 'VAT').", max_length=64, null=True, blank=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='DocumentEntry',
            fields=[
                ('id', models.AutoField(verbose_name='ID',
                 serialize=False, auto_created=True, primary_key=True)),
                ('description', models.CharField(max_length=255)),
                ('unit', models.CharField(
                    max_length=20, null=True, blank=True)),
                ('quantity', models.DecimalField(max_digits=19, decimal_places=2,
                 validators=[django.core.validators.MinValueValidator(0.0)])),
                ('unit_price', models.DecimalField(
                    max_digits=8, decimal_places=2)),
                ('start_date', models.DateField(null=True, blank=True)),
                ('end_date', models.DateField(null=True, blank=True)),
                ('prorated', models.BooleanField(default=False)),
            ],
            options={
                'verbose_name': 'Entry',
                'verbose_name_plural': 'Entries',
            },
        ),
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('id', models.AutoField(verbose_name='ID',
                 serialize=False, auto_created=True, primary_key=True)),
                ('number', models.IntegerField(null=True, blank=True)),
                ('archived_customer',
                 jsonfield.fields.JSONField(default=dict)),
                ('archived_provider',
                 jsonfield.fields.JSONField(default=dict)),
                ('due_date', models.DateField(null=True, blank=True)),
                ('issue_date', models.DateField(null=True, blank=True)),
                ('paid_date', models.DateField(null=True, blank=True)),
                ('cancel_date', models.DateField(null=True, blank=True)),
                ('sales_tax_percent', models.DecimalField(blank=True, null=True, max_digits=4,
                 decimal_places=2, validators=[django.core.validators.MinValueValidator(
                     0.0)])),
                ('sales_tax_name', models.CharField(
                    max_length=64, null=True, blank=True)),
                ('currency', models.CharField(default=b'USD', help_text=b'The currency used for billing.', max_length=4, choices=[('USD', 'USD - United States Dollar'), ('EUR', 'EUR - Euro Members'), ('JPY', 'JPY - Japan Yen'), ('GBP', 'GBP - United Kingdom Pound'), ('CHF', 'CHF - Switzerland Franc'), ('AED', 'AED - United Arab Emirates Dirham'), ('AFN', 'AFN - Afghanistan Afghani'), ('ALL', 'ALL - Albania Lek'), ('AMD', 'AMD - Armenia Dram'), ('ANG', 'ANG - Netherlands Antilles Guilder'), ('AOA', 'AOA - Angola Kwanza'), ('ARS', 'ARS - Argentina Peso'), ('AUD', 'AUD - Australia Dollar'), ('AWG', 'AWG - Aruba Guilder'), ('AZN', 'AZN - Azerbaijan New Manat'), ('BAM', 'BAM - Bosnia and Herzegovina Convertible Marka'), ('BBD', 'BBD - Barbados Dollar'), ('BDT', 'BDT - Bangladesh Taka'), ('BGN', 'BGN - Bulgaria Lev'), ('BHD', 'BHD - Bahrain Dinar'), ('BIF', 'BIF - Burundi Franc'), ('BMD', 'BMD - Bermuda Dollar'), ('BND', 'BND - Brunei Darussalam Dollar'), ('BOB', 'BOB - Bolivia Boliviano'), ('BRL', 'BRL - Brazil Real'), ('BSD', 'BSD - Bahamas Dollar'), ('BTN', 'BTN - Bhutan Ngultrum'), ('BWP', 'BWP - Botswana Pula'), ('BYR', 'BYR - Belarus Ruble'), ('BZD', 'BZD - Belize Dollar'), ('CAD', 'CAD - Canada Dollar'), ('CDF', 'CDF - Congo/Kinshasa Franc'), ('CLP', 'CLP - Chile Peso'), ('CNY', 'CNY - China Yuan Renminbi'), ('COP', 'COP - Colombia Peso'), ('CRC', 'CRC - Costa Rica Colon'), ('CUC', 'CUC - Cuba Convertible Peso'), ('CUP', 'CUP - Cuba Peso'), ('CVE', 'CVE - Cape Verde Escudo'), ('CZK', 'CZK - Czech Republic Koruna'), ('DJF', 'DJF - Djibouti Franc'), ('DKK', 'DKK - Denmark Krone'), ('DOP', 'DOP - Dominican Republic Peso'), ('DZD', 'DZD - Algeria Dinar'), ('EGP', 'EGP - Egypt Pound'), ('ERN', 'ERN - Eritrea Nakfa'), ('ETB', 'ETB - Ethiopia Birr'), ('FJD', 'FJD - Fiji Dollar'), ('FKP', 'FKP - Falkland Islands (Malvinas) Pound'), ('GEL', 'GEL - Georgia Lari'), ('GGP', 'GGP - Guernsey Pound'), ('GHS', 'GHS - Ghana Cedi'), ('GIP', 'GIP - Gibraltar Pound'), ('GMD', 'GMD - Gambia Dalasi'), ('GNF', 'GNF - Guinea Franc'), ('GTQ', 'GTQ - Guatemala Quetzal'), ('GYD', 'GYD - Guyana Dollar'), ('HKD', 'HKD - Hong Kong Dollar'), ('HNL', 'HNL - Honduras Lempira'), ('HRK', 'HRK - Croatia Kuna'), ('HTG', 'HTG - Haiti Gourde'), ('HUF', 'HUF - Hungary Forint'), ('IDR', 'IDR - Indonesia Rupiah'), ('ILS', 'ILS - Israel Shekel'), ('IMP', 'IMP - Isle of Man Pound'), ('INR', 'INR - India Rupee'), ('IQD', 'IQD - Iraq Dinar'), ('IRR', 'IRR - Iran Rial'), ('ISK', 'ISK - Iceland Krona'), ('JEP', 'JEP - Jersey Pound'), ('JMD', 'JMD - Jamaica Dollar'), ('JOD', 'JOD - Jordan Dinar'), ('KES', 'KES - Kenya Shilling'), ('KGS', 'KGS - Kyrgyzstan Som'), ('KHR', 'KHR - Cambodia Riel'), ('KMF', 'KMF - Comoros Franc'), ('KPW', 'KPW - Korea (North) Won'), ('KRW', 'KRW - Korea (South) Won'), ('KWD', 'KWD - Kuwait Dinar'), ('KYD', 'KYD - Cayman Islands Dollar'), ('KZT', 'KZT - Kazakhstan Tenge'), ('LAK', 'LAK - Laos Kip'), ('LBP', 'LBP - Lebanon Pound'), (
                    'LKR', 'LKR - Sri Lanka Rupee'), ('LRD', 'LRD - Liberia Dollar'), ('LSL', 'LSL - Lesotho Loti'), ('LTL', 'LTL - Lithuania Litas'), ('LVL', 'LVL - Latvia Lat'), ('LYD', 'LYD - Libya Dinar'), ('MAD', 'MAD - Morocco Dirham'), ('MDL', 'MDL - Moldova Le'), ('MGA', 'MGA - Madagascar Ariary'), ('MKD', 'MKD - Macedonia Denar'), ('MMK', 'MMK - Myanmar (Burma) Kyat'), ('MNT', 'MNT - Mongolia Tughrik'), ('MOP', 'MOP - Macau Pataca'), ('MRO', 'MRO - Mauritania Ouguiya'), ('MUR', 'MUR - Mauritius Rupee'), ('MVR', 'MVR - Maldives (Maldive Islands) Rufiyaa'), ('MWK', 'MWK - Malawi Kwacha'), ('MXN', 'MXN - Mexico Peso'), ('MYR', 'MYR - Malaysia Ringgit'), ('MZN', 'MZN - Mozambique Metical'), ('NAD', 'NAD - Namibia Dollar'), ('NGN', 'NGN - Nigeria Naira'), ('NIO', 'NIO - Nicaragua Cordoba'), ('NOK', 'NOK - Norway Krone'), ('NPR', 'NPR - Nepal Rupee'), ('NZD', 'NZD - New Zealand Dollar'), ('OMR', 'OMR - Oman Rial'), ('PAB', 'PAB - Panama Balboa'), ('PEN', 'PEN - Peru Nuevo Sol'), ('PGK', 'PGK - Papua New Guinea Kina'), ('PHP', 'PHP - Philippines Peso'), ('PKR', 'PKR - Pakistan Rupee'), ('PLN', 'PLN - Poland Zloty'), ('PYG', 'PYG - Paraguay Guarani'), ('QAR', 'QAR - Qatar Riyal'), ('RON', 'RON - Romania New Le'), ('RSD', 'RSD - Serbia Dinar'), ('RUB', 'RUB - Russia Ruble'), ('RWF', 'RWF - Rwanda Franc'), ('SAR', 'SAR - Saudi Arabia Riyal'), ('SBD', 'SBD - Solomon Islands Dollar'), ('SCR', 'SCR - Seychelles Rupee'), ('SDG', 'SDG - Sudan Pound'), ('SEK', 'SEK - Sweden Krona'), ('SGD', 'SGD - Singapore Dollar'), ('SHP', 'SHP - Saint Helena Pound'), ('SLL', 'SLL - Sierra Leone Leone'), ('SOS', 'SOS - Somalia Shilling'), ('SPL', 'SPL - Seborga Luigino'), ('SRD', 'SRD - Suriname Dollar'), ('STD', 'STD - S\xe3o Tom\xe9 and Pr\xedncipe Dobra'), ('SVC', 'SVC - El Salvador Colon'), ('SYP', 'SYP - Syria Pound'), ('SZL', 'SZL - Swaziland Lilangeni'), ('THB', 'THB - Thailand Baht'), ('TJS', 'TJS - Tajikistan Somoni'), ('TMT', 'TMT - Turkmenistan Manat'), ('TND', 'TND - Tunisia Dinar'), ('TOP', "TOP - Tonga Pa'anga"), ('TRY', 'TRY - Turkey Lira'), ('TTD', 'TTD - Trinidad and Tobago Dollar'), ('TVD', 'TVD - Tuvalu Dollar'), ('TWD', 'TWD - Taiwan New Dollar'), ('TZS', 'TZS - Tanzania Shilling'), ('UAH', 'UAH - Ukraine Hryvna'), ('UGX', 'UGX - Uganda Shilling'), ('UYU', 'UYU - Uruguay Peso'), ('UZS', 'UZS - Uzbekistan Som'), ('VEF', 'VEF - Venezuela Bolivar'), ('VND', 'VND - Viet Nam Dong'), ('VUV', 'VUV - Vanuatu Vat'), ('WST', 'WST - Samoa Tala'), ('XAF', 'XAF - Communaut\xe9 Financi\xe8re Africaine (BEAC) CFA Franc BEAC'), ('XCD', 'XCD - East Caribbean Dollar'), ('XDR', 'XDR - International Monetary Fund (IMF) Special Drawing Rights'), ('XOF', 'XOF - Communaut\xe9 Financi\xe8re Africaine (BCEAO) Franc'), ('XPF', 'XPF - Comptoirs Fran\xe7ais du Pacifique (CFP) Franc'), ('YER', 'YER - Yemen Rial'), ('ZAR', 'ZAR - South Africa Rand'), ('ZMK', 'ZMK - Zambia Kwacha'), ('ZWD', 'ZWD - Zimbabwe Dollar')])),
                ('pdf', models.FileField(
                    upload_to=silver.models.documents.base.documents_pdf_path, null=True, editable=False, blank=True)),
                ('state', django_fsm.FSMField(default=b'draft', help_text=b'The state the invoice is in.', max_length=10,
                 verbose_name=b'State', choices=[(b'draft', b'Draft'), (b'issued', b'Issued'), (b'paid', b'Paid'), (b'canceled', b'Canceled')])),
                ('customer', models.ForeignKey(to='silver.Customer')),
            ],
            options={
                'ordering': ('-issue_date', 'number'),
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='MeteredFeature',
            fields=[
                ('id', models.AutoField(verbose_name='ID',
                 serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(
                    help_text=b'The feature display name.', max_length=200)),
                ('unit', models.CharField(max_length=20)),
                ('price_per_unit', models.DecimalField(help_text=b'The price per unit.', max_digits=8,
                 decimal_places=2, validators=[django.core.validators.MinValueValidator(
                     0.0)])),
                ('included_units', models.DecimalField(help_text=b'The number of included units per plan interval.',
                 max_digits=19, decimal_places=2, validators=[django.core.validators.MinValueValidator(
                     0.0)])),
                ('included_units_during_trial', models.DecimalField(decimal_places=2, validators=[django.core.validators.MinValueValidator(
                    0.0)], max_digits=19, blank=True, help_text=b'The number of included units during the trial period.', null=True)),
            ],
        ),
        migrations.CreateModel(
            name='MeteredFeatureUnitsLog',
            fields=[
                ('id', models.AutoField(verbose_name='ID',
                 serialize=False, auto_created=True, primary_key=True)),
                ('consumed_units', models.DecimalField(max_digits=19, decimal_places=2,
                 validators=[django.core.validators.MinValueValidator(0.0)])),
                ('start_date', models.DateField(editable=False)),
                ('end_date', models.DateField(editable=False)),
                ('metered_feature', models.ForeignKey(
                    related_name='consumed', to='silver.MeteredFeature')),
            ],
        ),
        migrations.CreateModel(
            name='Plan',
            fields=[
                ('id', models.AutoField(verbose_name='ID',
                 serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(
                    help_text=b'Display name of the plan.', max_length=200)),
                ('interval', models.CharField(default=b'month', help_text=b'The frequency with which a subscription should be billed.',
                 max_length=12, choices=[(
                     b'day', b'Day'), (b'week', b'Week'), (b'month', b'Month'), (b'year', b'Year')])),
                ('interval_count', models.PositiveIntegerField(
                    help_text=b'The number of intervals between each subscription billing')),
                ('amount', models.DecimalField(help_text=b'The amount in the specified currency to be charged on the interval specified.',
                 max_digits=8, decimal_places=2, validators=[django.core.validators.MinValueValidator(
                     0.0)])),
                ('currency', models.CharField(default=b'USD', help_text=b'The currency in which the subscription will be charged.', max_length=4, choices=[('USD', 'USD - United States Dollar'), ('EUR', 'EUR - Euro Members'), ('JPY', 'JPY - Japan Yen'), ('GBP', 'GBP - United Kingdom Pound'), ('CHF', 'CHF - Switzerland Franc'), ('AED', 'AED - United Arab Emirates Dirham'), ('AFN', 'AFN - Afghanistan Afghani'), ('ALL', 'ALL - Albania Lek'), ('AMD', 'AMD - Armenia Dram'), ('ANG', 'ANG - Netherlands Antilles Guilder'), ('AOA', 'AOA - Angola Kwanza'), ('ARS', 'ARS - Argentina Peso'), ('AUD', 'AUD - Australia Dollar'), ('AWG', 'AWG - Aruba Guilder'), ('AZN', 'AZN - Azerbaijan New Manat'), ('BAM', 'BAM - Bosnia and Herzegovina Convertible Marka'), ('BBD', 'BBD - Barbados Dollar'), ('BDT', 'BDT - Bangladesh Taka'), ('BGN', 'BGN - Bulgaria Lev'), ('BHD', 'BHD - Bahrain Dinar'), ('BIF', 'BIF - Burundi Franc'), ('BMD', 'BMD - Bermuda Dollar'), ('BND', 'BND - Brunei Darussalam Dollar'), ('BOB', 'BOB - Bolivia Boliviano'), ('BRL', 'BRL - Brazil Real'), ('BSD', 'BSD - Bahamas Dollar'), ('BTN', 'BTN - Bhutan Ngultrum'), ('BWP', 'BWP - Botswana Pula'), ('BYR', 'BYR - Belarus Ruble'), ('BZD', 'BZD - Belize Dollar'), ('CAD', 'CAD - Canada Dollar'), ('CDF', 'CDF - Congo/Kinshasa Franc'), ('CLP', 'CLP - Chile Peso'), ('CNY', 'CNY - China Yuan Renminbi'), ('COP', 'COP - Colombia Peso'), ('CRC', 'CRC - Costa Rica Colon'), ('CUC', 'CUC - Cuba Convertible Peso'), ('CUP', 'CUP - Cuba Peso'), ('CVE', 'CVE - Cape Verde Escudo'), ('CZK', 'CZK - Czech Republic Koruna'), ('DJF', 'DJF - Djibouti Franc'), ('DKK', 'DKK - Denmark Krone'), ('DOP', 'DOP - Dominican Republic Peso'), ('DZD', 'DZD - Algeria Dinar'), ('EGP', 'EGP - Egypt Pound'), ('ERN', 'ERN - Eritrea Nakfa'), ('ETB', 'ETB - Ethiopia Birr'), ('FJD', 'FJD - Fiji Dollar'), ('FKP', 'FKP - Falkland Islands (Malvinas) Pound'), ('GEL', 'GEL - Georgia Lari'), ('GGP', 'GGP - Guernsey Pound'), ('GHS', 'GHS - Ghana Cedi'), ('GIP', 'GIP - Gibraltar Pound'), ('GMD', 'GMD - Gambia Dalasi'), ('GNF', 'GNF - Guinea Franc'), ('GTQ', 'GTQ - Guatemala Quetzal'), ('GYD', 'GYD - Guyana Dollar'), ('HKD', 'HKD - Hong Kong Dollar'), ('HNL', 'HNL - Honduras Lempira'), ('HRK', 'HRK - Croatia Kuna'), ('HTG', 'HTG - Haiti Gourde'), ('HUF', 'HUF - Hungary Forint'), ('IDR', 'IDR - Indonesia Rupiah'), ('ILS', 'ILS - Israel Shekel'), ('IMP', 'IMP - Isle of Man Pound'), ('INR', 'INR - India Rupee'), ('IQD', 'IQD - Iraq Dinar'), ('IRR', 'IRR - Iran Rial'), ('ISK', 'ISK - Iceland Krona'), ('JEP', 'JEP - Jersey Pound'), ('JMD', 'JMD - Jamaica Dollar'), ('JOD', 'JOD - Jordan Dinar'), ('KES', 'KES - Kenya Shilling'), ('KGS', 'KGS - Kyrgyzstan Som'), ('KHR', 'KHR - Cambodia Riel'), ('KMF', 'KMF - Comoros Franc'), ('KPW', 'KPW - Korea (North) Won'), ('KRW', 'KRW - Korea (South) Won'), ('KWD', 'KWD - Kuwait Dinar'), ('KYD', 'KYD - Cayman Islands Dollar'), ('KZT', 'KZT - Kazakhstan Tenge'), ('LAK', 'LAK - Laos Kip'), (
                    'LBP', 'LBP - Lebanon Pound'), ('LKR', 'LKR - Sri Lanka Rupee'), ('LRD', 'LRD - Liberia Dollar'), ('LSL', 'LSL - Lesotho Loti'), ('LTL', 'LTL - Lithuania Litas'), ('LVL', 'LVL - Latvia Lat'), ('LYD', 'LYD - Libya Dinar'), ('MAD', 'MAD - Morocco Dirham'), ('MDL', 'MDL - Moldova Le'), ('MGA', 'MGA - Madagascar Ariary'), ('MKD', 'MKD - Macedonia Denar'), ('MMK', 'MMK - Myanmar (Burma) Kyat'), ('MNT', 'MNT - Mongolia Tughrik'), ('MOP', 'MOP - Macau Pataca'), ('MRO', 'MRO - Mauritania Ouguiya'), ('MUR', 'MUR - Mauritius Rupee'), ('MVR', 'MVR - Maldives (Maldive Islands) Rufiyaa'), ('MWK', 'MWK - Malawi Kwacha'), ('MXN', 'MXN - Mexico Peso'), ('MYR', 'MYR - Malaysia Ringgit'), ('MZN', 'MZN - Mozambique Metical'), ('NAD', 'NAD - Namibia Dollar'), ('NGN', 'NGN - Nigeria Naira'), ('NIO', 'NIO - Nicaragua Cordoba'), ('NOK', 'NOK - Norway Krone'), ('NPR', 'NPR - Nepal Rupee'), ('NZD', 'NZD - New Zealand Dollar'), ('OMR', 'OMR - Oman Rial'), ('PAB', 'PAB - Panama Balboa'), ('PEN', 'PEN - Peru Nuevo Sol'), ('PGK', 'PGK - Papua New Guinea Kina'), ('PHP', 'PHP - Philippines Peso'), ('PKR', 'PKR - Pakistan Rupee'), ('PLN', 'PLN - Poland Zloty'), ('PYG', 'PYG - Paraguay Guarani'), ('QAR', 'QAR - Qatar Riyal'), ('RON', 'RON - Romania New Le'), ('RSD', 'RSD - Serbia Dinar'), ('RUB', 'RUB - Russia Ruble'), ('RWF', 'RWF - Rwanda Franc'), ('SAR', 'SAR - Saudi Arabia Riyal'), ('SBD', 'SBD - Solomon Islands Dollar'), ('SCR', 'SCR - Seychelles Rupee'), ('SDG', 'SDG - Sudan Pound'), ('SEK', 'SEK - Sweden Krona'), ('SGD', 'SGD - Singapore Dollar'), ('SHP', 'SHP - Saint Helena Pound'), ('SLL', 'SLL - Sierra Leone Leone'), ('SOS', 'SOS - Somalia Shilling'), ('SPL', 'SPL - Seborga Luigino'), ('SRD', 'SRD - Suriname Dollar'), ('STD', 'STD - S\xe3o Tom\xe9 and Pr\xedncipe Dobra'), ('SVC', 'SVC - El Salvador Colon'), ('SYP', 'SYP - Syria Pound'), ('SZL', 'SZL - Swaziland Lilangeni'), ('THB', 'THB - Thailand Baht'), ('TJS', 'TJS - Tajikistan Somoni'), ('TMT', 'TMT - Turkmenistan Manat'), ('TND', 'TND - Tunisia Dinar'), ('TOP', "TOP - Tonga Pa'anga"), ('TRY', 'TRY - Turkey Lira'), ('TTD', 'TTD - Trinidad and Tobago Dollar'), ('TVD', 'TVD - Tuvalu Dollar'), ('TWD', 'TWD - Taiwan New Dollar'), ('TZS', 'TZS - Tanzania Shilling'), ('UAH', 'UAH - Ukraine Hryvna'), ('UGX', 'UGX - Uganda Shilling'), ('UYU', 'UYU - Uruguay Peso'), ('UZS', 'UZS - Uzbekistan Som'), ('VEF', 'VEF - Venezuela Bolivar'), ('VND', 'VND - Viet Nam Dong'), ('VUV', 'VUV - Vanuatu Vat'), ('WST', 'WST - Samoa Tala'), ('XAF', 'XAF - Communaut\xe9 Financi\xe8re Africaine (BEAC) CFA Franc BEAC'), ('XCD', 'XCD - East Caribbean Dollar'), ('XDR', 'XDR - International Monetary Fund (IMF) Special Drawing Rights'), ('XOF', 'XOF - Communaut\xe9 Financi\xe8re Africaine (BCEAO) Franc'), ('XPF', 'XPF - Comptoirs Fran\xe7ais du Pacifique (CFP) Franc'), ('YER', 'YER - Yemen Rial'), ('ZAR', 'ZAR - South Africa Rand'), ('ZMK', 'ZMK - Zambia Kwacha'), ('ZWD', 'ZWD - Zimbabwe Dollar')])),
                ('trial_period_days', models.PositiveIntegerField(
                    help_text=b'Number of trial period days granted when subscribing a customer to this plan.', null=True)),
                ('generate_after', models.PositiveIntegerField(
                    default=0, help_text=b'Number of seconds to wait after current billing cycle ends before generating the invoice. This can be used to allow systems to finish updating feature counters.')),
                ('enabled', models.BooleanField(
                    default=True, help_text=b'Whether to accept subscriptions.')),
                ('private', models.BooleanField(
                    default=False, help_text=b'Indicates if a plan is private.')),
                ('metered_features', models.ManyToManyField(
                    help_text=b"A list of the plan's metered features.", to='silver.MeteredFeature', blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='ProductCode',
            fields=[
                ('id', models.AutoField(verbose_name='ID',
                 serialize=False, auto_created=True, primary_key=True)),
                ('value', models.CharField(unique=True, max_length=128)),
            ],
        ),
        migrations.CreateModel(
            name='Proforma',
            fields=[
                ('id', models.AutoField(verbose_name='ID',
                 serialize=False, auto_created=True, primary_key=True)),
                ('number', models.IntegerField(null=True, blank=True)),
                ('archived_customer',
                 jsonfield.fields.JSONField(default=dict)),
                ('archived_provider',
                 jsonfield.fields.JSONField(default=dict)),
                ('due_date', models.DateField(null=True, blank=True)),
                ('issue_date', models.DateField(null=True, blank=True)),
                ('paid_date', models.DateField(null=True, blank=True)),
                ('cancel_date', models.DateField(null=True, blank=True)),
                ('sales_tax_percent', models.DecimalField(blank=True, null=True, max_digits=4,
                 decimal_places=2, validators=[django.core.validators.MinValueValidator(
                     0.0)])),
                ('sales_tax_name', models.CharField(
                    max_length=64, null=True, blank=True)),
                ('currency', models.CharField(default=b'USD', help_text=b'The currency used for billing.', max_length=4, choices=[('USD', 'USD - United States Dollar'), ('EUR', 'EUR - Euro Members'), ('JPY', 'JPY - Japan Yen'), ('GBP', 'GBP - United Kingdom Pound'), ('CHF', 'CHF - Switzerland Franc'), ('AED', 'AED - United Arab Emirates Dirham'), ('AFN', 'AFN - Afghanistan Afghani'), ('ALL', 'ALL - Albania Lek'), ('AMD', 'AMD - Armenia Dram'), ('ANG', 'ANG - Netherlands Antilles Guilder'), ('AOA', 'AOA - Angola Kwanza'), ('ARS', 'ARS - Argentina Peso'), ('AUD', 'AUD - Australia Dollar'), ('AWG', 'AWG - Aruba Guilder'), ('AZN', 'AZN - Azerbaijan New Manat'), ('BAM', 'BAM - Bosnia and Herzegovina Convertible Marka'), ('BBD', 'BBD - Barbados Dollar'), ('BDT', 'BDT - Bangladesh Taka'), ('BGN', 'BGN - Bulgaria Lev'), ('BHD', 'BHD - Bahrain Dinar'), ('BIF', 'BIF - Burundi Franc'), ('BMD', 'BMD - Bermuda Dollar'), ('BND', 'BND - Brunei Darussalam Dollar'), ('BOB', 'BOB - Bolivia Boliviano'), ('BRL', 'BRL - Brazil Real'), ('BSD', 'BSD - Bahamas Dollar'), ('BTN', 'BTN - Bhutan Ngultrum'), ('BWP', 'BWP - Botswana Pula'), ('BYR', 'BYR - Belarus Ruble'), ('BZD', 'BZD - Belize Dollar'), ('CAD', 'CAD - Canada Dollar'), ('CDF', 'CDF - Congo/Kinshasa Franc'), ('CLP', 'CLP - Chile Peso'), ('CNY', 'CNY - China Yuan Renminbi'), ('COP', 'COP - Colombia Peso'), ('CRC', 'CRC - Costa Rica Colon'), ('CUC', 'CUC - Cuba Convertible Peso'), ('CUP', 'CUP - Cuba Peso'), ('CVE', 'CVE - Cape Verde Escudo'), ('CZK', 'CZK - Czech Republic Koruna'), ('DJF', 'DJF - Djibouti Franc'), ('DKK', 'DKK - Denmark Krone'), ('DOP', 'DOP - Dominican Republic Peso'), ('DZD', 'DZD - Algeria Dinar'), ('EGP', 'EGP - Egypt Pound'), ('ERN', 'ERN - Eritrea Nakfa'), ('ETB', 'ETB - Ethiopia Birr'), ('FJD', 'FJD - Fiji Dollar'), ('FKP', 'FKP - Falkland Islands (Malvinas) Pound'), ('GEL', 'GEL - Georgia Lari'), ('GGP', 'GGP - Guernsey Pound'), ('GHS', 'GHS - Ghana Cedi'), ('GIP', 'GIP - Gibraltar Pound'), ('GMD', 'GMD - Gambia Dalasi'), ('GNF', 'GNF - Guinea Franc'), ('GTQ', 'GTQ - Guatemala Quetzal'), ('GYD', 'GYD - Guyana Dollar'), ('HKD', 'HKD - Hong Kong Dollar'), ('HNL', 'HNL - Honduras Lempira'), ('HRK', 'HRK - Croatia Kuna'), ('HTG', 'HTG - Haiti Gourde'), ('HUF', 'HUF - Hungary Forint'), ('IDR', 'IDR - Indonesia Rupiah'), ('ILS', 'ILS - Israel Shekel'), ('IMP', 'IMP - Isle of Man Pound'), ('INR', 'INR - India Rupee'), ('IQD', 'IQD - Iraq Dinar'), ('IRR', 'IRR - Iran Rial'), ('ISK', 'ISK - Iceland Krona'), ('JEP', 'JEP - Jersey Pound'), ('JMD', 'JMD - Jamaica Dollar'), ('JOD', 'JOD - Jordan Dinar'), ('KES', 'KES - Kenya Shilling'), ('KGS', 'KGS - Kyrgyzstan Som'), ('KHR', 'KHR - Cambodia Riel'), ('KMF', 'KMF - Comoros Franc'), ('KPW', 'KPW - Korea (North) Won'), ('KRW', 'KRW - Korea (South) Won'), ('KWD', 'KWD - Kuwait Dinar'), ('KYD', 'KYD - Cayman Islands Dollar'), ('KZT', 'KZT - Kazakhstan Tenge'), ('LAK', 'LAK - Laos Kip'), ('LBP', 'LBP - Lebanon Pound'), (
                    'LKR', 'LKR - Sri Lanka Rupee'), ('LRD', 'LRD - Liberia Dollar'), ('LSL', 'LSL - Lesotho Loti'), ('LTL', 'LTL - Lithuania Litas'), ('LVL', 'LVL - Latvia Lat'), ('LYD', 'LYD - Libya Dinar'), ('MAD', 'MAD - Morocco Dirham'), ('MDL', 'MDL - Moldova Le'), ('MGA', 'MGA - Madagascar Ariary'), ('MKD', 'MKD - Macedonia Denar'), ('MMK', 'MMK - Myanmar (Burma) Kyat'), ('MNT', 'MNT - Mongolia Tughrik'), ('MOP', 'MOP - Macau Pataca'), ('MRO', 'MRO - Mauritania Ouguiya'), ('MUR', 'MUR - Mauritius Rupee'), ('MVR', 'MVR - Maldives (Maldive Islands) Rufiyaa'), ('MWK', 'MWK - Malawi Kwacha'), ('MXN', 'MXN - Mexico Peso'), ('MYR', 'MYR - Malaysia Ringgit'), ('MZN', 'MZN - Mozambique Metical'), ('NAD', 'NAD - Namibia Dollar'), ('NGN', 'NGN - Nigeria Naira'), ('NIO', 'NIO - Nicaragua Cordoba'), ('NOK', 'NOK - Norway Krone'), ('NPR', 'NPR - Nepal Rupee'), ('NZD', 'NZD - New Zealand Dollar'), ('OMR', 'OMR - Oman Rial'), ('PAB', 'PAB - Panama Balboa'), ('PEN', 'PEN - Peru Nuevo Sol'), ('PGK', 'PGK - Papua New Guinea Kina'), ('PHP', 'PHP - Philippines Peso'), ('PKR', 'PKR - Pakistan Rupee'), ('PLN', 'PLN - Poland Zloty'), ('PYG', 'PYG - Paraguay Guarani'), ('QAR', 'QAR - Qatar Riyal'), ('RON', 'RON - Romania New Le'), ('RSD', 'RSD - Serbia Dinar'), ('RUB', 'RUB - Russia Ruble'), ('RWF', 'RWF - Rwanda Franc'), ('SAR', 'SAR - Saudi Arabia Riyal'), ('SBD', 'SBD - Solomon Islands Dollar'), ('SCR', 'SCR - Seychelles Rupee'), ('SDG', 'SDG - Sudan Pound'), ('SEK', 'SEK - Sweden Krona'), ('SGD', 'SGD - Singapore Dollar'), ('SHP', 'SHP - Saint Helena Pound'), ('SLL', 'SLL - Sierra Leone Leone'), ('SOS', 'SOS - Somalia Shilling'), ('SPL', 'SPL - Seborga Luigino'), ('SRD', 'SRD - Suriname Dollar'), ('STD', 'STD - S\xe3o Tom\xe9 and Pr\xedncipe Dobra'), ('SVC', 'SVC - El Salvador Colon'), ('SYP', 'SYP - Syria Pound'), ('SZL', 'SZL - Swaziland Lilangeni'), ('THB', 'THB - Thailand Baht'), ('TJS', 'TJS - Tajikistan Somoni'), ('TMT', 'TMT - Turkmenistan Manat'), ('TND', 'TND - Tunisia Dinar'), ('TOP', "TOP - Tonga Pa'anga"), ('TRY', 'TRY - Turkey Lira'), ('TTD', 'TTD - Trinidad and Tobago Dollar'), ('TVD', 'TVD - Tuvalu Dollar'), ('TWD', 'TWD - Taiwan New Dollar'), ('TZS', 'TZS - Tanzania Shilling'), ('UAH', 'UAH - Ukraine Hryvna'), ('UGX', 'UGX - Uganda Shilling'), ('UYU', 'UYU - Uruguay Peso'), ('UZS', 'UZS - Uzbekistan Som'), ('VEF', 'VEF - Venezuela Bolivar'), ('VND', 'VND - Viet Nam Dong'), ('VUV', 'VUV - Vanuatu Vat'), ('WST', 'WST - Samoa Tala'), ('XAF', 'XAF - Communaut\xe9 Financi\xe8re Africaine (BEAC) CFA Franc BEAC'), ('XCD', 'XCD - East Caribbean Dollar'), ('XDR', 'XDR - International Monetary Fund (IMF) Special Drawing Rights'), ('XOF', 'XOF - Communaut\xe9 Financi\xe8re Africaine (BCEAO) Franc'), ('XPF', 'XPF - Comptoirs Fran\xe7ais du Pacifique (CFP) Franc'), ('YER', 'YER - Yemen Rial'), ('ZAR', 'ZAR - South Africa Rand'), ('ZMK', 'ZMK - Zambia Kwacha'), ('ZWD', 'ZWD - Zimbabwe Dollar')])),
                ('pdf', models.FileField(
                    upload_to=silver.models.documents.base.documents_pdf_path, null=True, editable=False, blank=True)),
                ('state', django_fsm.FSMField(default=b'draft', help_text=b'The state the invoice is in.', max_length=10,
                 verbose_name=b'State', choices=[(b'draft', b'Draft'), (b'issued', b'Issued'), (b'paid', b'Paid'), (b'canceled', b'Canceled')])),
                ('customer', models.ForeignKey(to='silver.Customer')),
                ('invoice', models.ForeignKey(
                    related_name='related_invoice', blank=True, to='silver.Invoice', null=True)),
            ],
            options={
                'ordering': ('-issue_date', 'number'),
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Provider',
            fields=[
                ('id', models.AutoField(verbose_name='ID',
                 serialize=False, auto_created=True, primary_key=True)),
                ('live', livefield.fields.LiveField(default=True)),
                ('name', models.CharField(
                    help_text=b'The name to be used for billing purposes.', max_length=128)),
                ('company', models.CharField(
                    max_length=128, null=True, blank=True)),
                ('email', models.EmailField(
                    max_length=254, null=True, blank=True)),
                ('address_1', models.CharField(max_length=128)),
                ('address_2', models.CharField(
                    max_length=128, null=True, blank=True)),
                ('country', models.CharField(max_length=3, choices=[('AF', 'Afghanistan'), ('AL', 'Albania'), ('AQ', 'Antarctica'), ('DZ', 'Algeria'), ('AS', 'American Samoa'), ('AD', 'Andorra'), ('AO', 'Angola'), ('AG', 'Antigua and Barbuda'), ('AZ', 'Azerbaijan'), ('AR', 'Argentina'), ('AU', 'Australia'), ('AT', 'Austria'), ('BS', 'Bahamas'), ('BH', 'Bahrain'), ('BD', 'Bangladesh'), ('AM', 'Armenia'), ('BB', 'Barbados'), ('BE', 'Belgium'), ('BM', 'Bermuda'), ('BT', 'Bhutan'), ('BO', 'Bolivia'), ('BA', 'Bosnia and Herzegovina'), ('BW', 'Botswana'), ('BV', 'Bouvet Island'), ('BR', 'Brazil'), ('BZ', 'Belize'), ('IO', 'British Indian Ocean Territory'), ('SB', 'Solomon Islands'), ('VG', 'British Virgin Islands'), ('BN', 'Brunei Darussalam'), ('BG', 'Bulgaria'), ('MM', 'Myanmar'), ('BI', 'Burundi'), ('BY', 'Belarus'), ('KH', 'Cambodia'), ('CM', 'Cameroon'), ('CA', 'Canada'), ('CV', 'Cape Verde'), ('KY', 'Cayman Islands'), ('CF', 'Central African Republic'), ('LK', 'Sri Lanka'), ('TD', 'Chad'), ('CL', 'Chile'), ('CN', 'China'), ('TW', 'Taiwan'), ('CX', 'Christmas Island'), ('CC', 'Cocos'), ('CO', 'Colombia'), ('KM', 'Comoros'), ('YT', 'Mayotte'), ('CG', 'Congo'), ('CD', 'Congo'), ('CK', 'Cook Islands'), ('CR', 'Costa Rica'), ('HR', 'Croatia'), ('CU', 'Cuba'), ('CY', 'Cyprus'), ('CZ', 'Czech Republic'), ('BJ', 'Benin'), ('DK', 'Denmark'), ('DM', 'Dominica'), ('DO', 'Dominican Republic'), ('EC', 'Ecuador'), ('SV', 'El Salvador'), ('GQ', 'Equatorial Guinea'), ('ET', 'Ethiopia'), ('ER', 'Eritrea'), ('EE', 'Estonia'), ('FO', 'Faroe Islands'), ('FK', 'Falkland Islands'), ('GS', 'South Georgia and the South Sandwich Islands'), ('FJ', 'Fiji'), ('FI', 'Finland'), ('AX', '\xc5land Islands'), ('FR', 'France'), ('GF', 'French Guiana'), ('PF', 'French Polynesia'), ('TF', 'French Southern Territories'), ('DJ', 'Djibouti'), ('GA', 'Gabon'), ('GE', 'Georgia'), ('GM', 'Gambia'), ('PS', 'Palestinian Territory'), ('DE', 'Germany'), ('GH', 'Ghana'), ('GI', 'Gibraltar'), ('KI', 'Kiribati'), ('GR', 'Greece'), ('GL', 'Greenland'), ('GD', 'Grenada'), ('GP', 'Guadeloupe'), ('GU', 'Guam'), ('GT', 'Guatemala'), ('GN', 'Guinea'), ('GY', 'Guyana'), ('HT', 'Haiti'), ('HM', 'Heard Island and McDonald Islands'), ('VA', 'Holy See'), ('HN', 'Honduras'), ('HK', 'Hong Kong'), ('HU', 'Hungary'), ('IS', 'Iceland'), ('IN', 'India'), ('ID', 'Indonesia'), ('IR', 'Iran'), ('IQ', 'Iraq'), ('IE', 'Ireland'), ('IL', 'Israel'), ('IT', 'Italy'), ('CI', "Cote d'Ivoire"), ('JM', 'Jamaica'), ('JP', 'Japan'), ('KZ', 'Kazakhstan'), ('JO', 'Jordan'), ('KE', 'Kenya'), ('KP', 'Korea'), ('KR', 'Korea'), ('KW', 'Kuwait'), ('KG', 'Kyrgyz Republic'), ('LA', "Lao People's Democratic Republic"), ('LB', 'Lebanon'), ('LS', 'Lesotho'), ('LV', 'Latvia'), ('LR', 'Liberia'), ('LY', 'Libyan Arab Jamahiriya'), ('LI', 'Liechtenstein'), ('LT', 'Lithuania'), ('LU', 'Luxembourg'), ('MO', 'Macao'), (
                    'MG', 'Madagascar'), ('MW', 'Malawi'), ('MY', 'Malaysia'), ('MV', 'Maldives'), ('ML', 'Mali'), ('MT', 'Malta'), ('MQ', 'Martinique'), ('MR', 'Mauritania'), ('MU', 'Mauritius'), ('MX', 'Mexico'), ('MC', 'Monaco'), ('MN', 'Mongolia'), ('MD', 'Moldova'), ('ME', 'Montenegro'), ('MS', 'Montserrat'), ('MA', 'Morocco'), ('MZ', 'Mozambique'), ('OM', 'Oman'), ('NA', 'Namibia'), ('NR', 'Nauru'), ('NP', 'Nepal'), ('NL', 'Netherlands'), ('AN', 'Netherlands Antilles'), ('CW', 'Cura\xe7ao'), ('AW', 'Aruba'), ('SX', 'Sint Maarten'), ('BQ', 'Bonaire'), ('NC', 'New Caledonia'), ('VU', 'Vanuatu'), ('NZ', 'New Zealand'), ('NI', 'Nicaragua'), ('NE', 'Niger'), ('NG', 'Nigeria'), ('NU', 'Niue'), ('NF', 'Norfolk Island'), ('NO', 'Norway'), ('MP', 'Northern Mariana Islands'), ('UM', 'United States Minor Outlying Islands'), ('FM', 'Micronesia'), ('MH', 'Marshall Islands'), ('PW', 'Palau'), ('PK', 'Pakistan'), ('PA', 'Panama'), ('PG', 'Papua New Guinea'), ('PY', 'Paraguay'), ('PE', 'Peru'), ('PH', 'Philippines'), ('PN', 'Pitcairn Islands'), ('PL', 'Poland'), ('PT', 'Portugal'), ('GW', 'Guinea-Bissau'), ('TL', 'Timor-Leste'), ('PR', 'Puerto Rico'), ('QA', 'Qatar'), ('RE', 'Reunion'), ('RO', 'Romania'), ('RU', 'Russian Federation'), ('RW', 'Rwanda'), ('BL', 'Saint Barthelemy'), ('SH', 'Saint Helena'), ('KN', 'Saint Kitts and Nevis'), ('AI', 'Anguilla'), ('LC', 'Saint Lucia'), ('MF', 'Saint Martin'), ('PM', 'Saint Pierre and Miquelon'), ('VC', 'Saint Vincent and the Grenadines'), ('SM', 'San Marino'), ('ST', 'Sao Tome and Principe'), ('SA', 'Saudi Arabia'), ('SN', 'Senegal'), ('RS', 'Serbia'), ('SC', 'Seychelles'), ('SL', 'Sierra Leone'), ('SG', 'Singapore'), ('SK', 'Slovakia'), ('VN', 'Vietnam'), ('SI', 'Slovenia'), ('SO', 'Somalia'), ('ZA', 'South Africa'), ('ZW', 'Zimbabwe'), ('ES', 'Spain'), ('SS', 'South Sudan'), ('EH', 'Western Sahara'), ('SD', 'Sudan'), ('SR', 'Suriname'), ('SJ', 'Svalbard & Jan Mayen Islands'), ('SZ', 'Swaziland'), ('SE', 'Sweden'), ('CH', 'Switzerland'), ('SY', 'Syrian Arab Republic'), ('TJ', 'Tajikistan'), ('TH', 'Thailand'), ('TG', 'Togo'), ('TK', 'Tokelau'), ('TO', 'Tonga'), ('TT', 'Trinidad and Tobago'), ('AE', 'United Arab Emirates'), ('TN', 'Tunisia'), ('TR', 'Turkey'), ('TM', 'Turkmenistan'), ('TC', 'Turks and Caicos Islands'), ('TV', 'Tuvalu'), ('UG', 'Uganda'), ('UA', 'Ukraine'), ('MK', 'Macedonia'), ('EG', 'Egypt'), ('GB', 'United Kingdom'), ('GG', 'Guernsey'), ('JE', 'Jersey'), ('IM', 'Isle of Man'), ('TZ', 'Tanzania'), ('US', 'United States'), ('VI', 'United States Virgin Islands'), ('BF', 'Burkina Faso'), ('UY', 'Uruguay'), ('UZ', 'Uzbekistan'), ('VE', 'Venezuela'), ('WF', 'Wallis and Futuna'), ('WS', 'Samoa'), ('YE', 'Yemen'), ('ZM', 'Zambia'), ('XX', 'Disputed Territory'), ('XE', 'Iraq-Saudi Arabia Neutral Zone'), ('XD', 'United Nations Neutral Zone'), ('XS', 'Spratly Islands'), ('XS', 'Spratly Islands')])),
                ('city', models.CharField(max_length=128)),
                ('state', models.CharField(
                    max_length=128, null=True, blank=True)),
                ('zip_code', models.CharField(
                    max_length=32, null=True, blank=True)),
                ('extra', models.TextField(
                    help_text=b'Extra information to display on the invoice (markdown formatted).', null=True, blank=True)),
                ('flow', models.CharField(default=b'proforma', help_text=b'One of the available workflows for generating proformas and                   invoices (see the documentation for more details).',
                 max_length=10, choices=[(
                     b'proforma', b'Proforma'), (b'invoice', b'Invoice')])),
                ('invoice_series', models.CharField(
                    help_text=b'The series that will be used on every invoice generated by                   this provider.', max_length=20)),
                ('invoice_starting_number', models.PositiveIntegerField()),
                ('proforma_series', models.CharField(
                    help_text=b'The series that will be used on every proforma generated by                   this provider.', max_length=20, null=True, blank=True)),
                ('proforma_starting_number',
                 models.PositiveIntegerField(null=True, blank=True)),
                ('default_document_state', models.CharField(default=b'draft', help_text=b'The default state of the auto-generated documents.',
                 max_length=10, choices=[(
                     b'draft', b'Draft'), (b'issued', b'Issued')])),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Subscription',
            fields=[
                ('id', models.AutoField(verbose_name='ID',
                 serialize=False, auto_created=True, primary_key=True)),
                ('description', models.CharField(
                    max_length=1024, null=True, blank=True)),
                ('trial_end', models.DateField(
                    help_text=b'The date at which the trial ends. If set, overrides the computed trial end date from the plan.', null=True, blank=True)),
                ('start_date', models.DateField(
                    help_text=b'The starting date for the subscription.', null=True, blank=True)),
                ('ended_at', models.DateField(
                    help_text=b'The date when the subscription ended.', null=True, blank=True)),
                ('reference', models.CharField(
                    help_text=b"The subscription's reference in an external system.", max_length=128, null=True, blank=True)),
                ('state', django_fsm.FSMField(default=b'inactive', help_text=b'The state the subscription is in.', protected=True,
                 max_length=12, choices=[(
                     b'active', b'Active'), (b'inactive', b'Inactive'), (b'canceled', b'Canceled'), (b'ended', b'Ended')])),
                ('customer', models.ForeignKey(related_name='subscriptions',
                 to='silver.Customer', help_text=b'The customer who is subscribed to the plan.')),
                ('plan', models.ForeignKey(
                    help_text=b'The plan the customer is subscribed to.', to='silver.Plan')),
            ],
        ),
        migrations.AddField(
            model_name='proforma',
            name='provider',
            field=models.ForeignKey(to='silver.Provider'),
        ),
        migrations.AddField(
            model_name='plan',
            name='product_code',
            field=models.OneToOneField(
                to='silver.ProductCode',
                help_text=b'The product code for this plan.'),
        ),
        migrations.AddField(
            model_name='plan',
            name='provider',
            field=models.ForeignKey(
                related_name='plans',
                to='silver.Provider',
                help_text=b'The provider which provides the plan.'),
        ),
        migrations.AddField(
            model_name='meteredfeatureunitslog',
            name='subscription',
            field=models.ForeignKey(
                related_name='mf_log_entries',
                to='silver.Subscription'),
        ),
        migrations.AddField(
            model_name='meteredfeature',
            name='product_code',
            field=silver.utils.models.UnsavedForeignKey(
                help_text=b'The product code for this plan.',
                to='silver.ProductCode'),
        ),
        migrations.AddField(
            model_name='invoice',
            name='proforma',
            field=models.ForeignKey(
                related_name='related_proforma',
                blank=True,
                to='silver.Proforma',
                null=True),
        ),
        migrations.AddField(
            model_name='invoice',
            name='provider',
            field=models.ForeignKey(to='silver.Provider'),
        ),
        migrations.AddField(
            model_name='documententry',
            name='invoice',
            field=models.ForeignKey(
                related_name='invoice_entries',
                blank=True,
                to='silver.Invoice',
                null=True),
        ),
        migrations.AddField(
            model_name='documententry',
            name='product_code',
            field=models.ForeignKey(
                related_name='invoices',
                blank=True,
                to='silver.ProductCode',
                null=True),
        ),
        migrations.AddField(
            model_name='documententry',
            name='proforma',
            field=models.ForeignKey(
                related_name='proforma_entries',
                blank=True,
                to='silver.Proforma',
                null=True),
        ),
        migrations.AddField(
            model_name='billinglog',
            name='invoice',
            field=models.ForeignKey(
                related_name='billing_log_entries',
                blank=True,
                to='silver.Invoice',
                null=True),
        ),
        migrations.AddField(
            model_name='billinglog',
            name='proforma',
            field=models.ForeignKey(
                related_name='billing_log_entries',
                blank=True,
                to='silver.Proforma',
                null=True),
        ),
        migrations.AddField(
            model_name='billinglog',
            name='subscription',
            field=models.ForeignKey(
                related_name='billing_log_entries',
                to='silver.Subscription'),
        ),
        migrations.AlterUniqueTogether(
            name='proforma',
            unique_together=set([('provider', 'number')]),
        ),
        migrations.AlterUniqueTogether(
            name='meteredfeatureunitslog',
            unique_together=set(
                [('metered_feature',
                 'subscription',
                  'start_date',
                  'end_date')]),
        ),
        migrations.AlterUniqueTogether(
            name='invoice',
            unique_together=set([('provider', 'number')]),
        ),
    ]
