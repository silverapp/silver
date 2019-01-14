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

from __future__ import absolute_import

from rest_framework import serializers

from silver.api.serializers.common import CustomerUrl, PDFUrl
from silver.api.serializers.transaction_serializers import TransactionSerializer
from silver.models import DocumentEntry, Customer, Invoice, Proforma, BillingDocumentBase
from silver.utils.serializers import AutoCleanSerializerMixin


class DocumentEntrySerializer(AutoCleanSerializerMixin,
                              serializers.HyperlinkedModelSerializer):
    product_code = serializers.SlugRelatedField(
        slug_field='value',
        read_only=True
    )

    class Meta:
        model = DocumentEntry
        fields = ('description', 'unit', 'unit_price', 'quantity', 'total',
                  'total_before_tax', 'start_date', 'end_date', 'prorated',
                  'product_code')


class DocumentUrl(serializers.HyperlinkedIdentityField):
    def __init__(self, proforma_view_name, invoice_view_name, *args, **kwargs):
        # the view_name is required on HIF init, but we only know what it will
        # be in get_url
        kwargs['view_name'] = ''
        super(DocumentUrl, self).__init__(*args, **kwargs)

        self.invoice_view_name = invoice_view_name
        self.proforma_view_name = proforma_view_name

    def get_url(self, obj, view_name, request, format):
        view_name = (self.invoice_view_name if obj.kind == 'invoice' else
                     self.proforma_view_name)

        lookup_value = getattr(obj, self.lookup_field)

        if not lookup_value:
            return

        kwargs = {
            self.lookup_url_kwarg: str(lookup_value)
        }

        return self.reverse(view_name, kwargs=kwargs,
                            request=request, format=format)


class DocumentSerializer(serializers.HyperlinkedModelSerializer):
    """
        A read-only serializers for Proformas and Invoices
    """
    customer = CustomerUrl(view_name='customer-detail',
                           queryset=Customer.objects.all())
    pdf_url = PDFUrl(view_name='pdf', source='*', read_only=True)
    url = DocumentUrl(proforma_view_name='proforma-detail',
                      invoice_view_name='invoice-detail', )

    transactions = serializers.SerializerMethodField()

    def get_transactions(self, document):
        if document.kind == 'invoice':
            transactions = document.invoice_transactions.all()
        elif document.kind == 'proforma':
            transactions = document.proforma_transactions.all()
        else:
            return []

        for transaction in transactions:
            # This is done to avoid prefetching already prefetched resources
            transaction.payment_method.customer = document.customer
            transaction.provider = document.provider

        return TransactionSerializer(transactions, many=True,
                                     context=self.context).data

    class Meta:
        model = BillingDocumentBase
        fields = ('id', 'url', 'kind', 'series', 'number', 'provider',
                  'customer', 'due_date', 'issue_date', 'paid_date',
                  'cancel_date', 'sales_tax_name', 'sales_tax_percent',
                  'transaction_currency', 'currency', 'state', 'total',
                  'total_in_transaction_currency', 'pdf_url', 'transactions')
        read_only_fields = fields


class InvoiceSerializer(AutoCleanSerializerMixin,
                        serializers.HyperlinkedModelSerializer):
    invoice_entries = DocumentEntrySerializer(many=True, required=False)
    pdf_url = PDFUrl(view_name='pdf', source='*', read_only=True)
    customer = CustomerUrl(view_name='customer-detail',
                           queryset=Customer.objects.all())
    transactions = TransactionSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = ('id', 'series', 'number', 'provider', 'customer',
                  'archived_provider', 'archived_customer', 'due_date',
                  'issue_date', 'paid_date', 'cancel_date', 'sales_tax_name',
                  'sales_tax_percent', 'currency', 'transaction_currency',
                  'transaction_xe_rate', 'transaction_xe_date', 'state', 'proforma',
                  'invoice_entries', 'total', 'total_in_transaction_currency',
                  'pdf_url', 'transactions')
        read_only_fields = ('archived_provider', 'archived_customer', 'total',
                            'total_in_transaction_currency')
        extra_kwargs = {
            'transaction_currency': {'required': False},
            'proforma': {'source': 'related_document', 'view_name': 'proforma-detail'}
        }

    def create(self, validated_data):
        entries = validated_data.pop('invoice_entries', [])

        # Create the new invoice object
        invoice = Invoice.objects.create(**validated_data)

        # Add the invoice entries
        for entry in entries:
            entry_dict = dict()
            entry_dict['invoice'] = invoice
            for field in entry.items():
                entry_dict[field[0]] = field[1]

            DocumentEntry.objects.create(**entry_dict)

        return invoice

    def update(self, instance, validated_data):
        # The provider has changed => force the generation of the correct number
        # corresponding to the count of the new provider
        current_provider = instance.provider
        new_provider = validated_data.get('provider')
        if new_provider and new_provider != current_provider:
            instance.number = None

        updateable_fields = instance.updateable_fields
        for field_name in updateable_fields:
            field_value = validated_data.get(field_name,
                                             getattr(instance, field_name))
            setattr(instance, field_name, field_value)
        instance.save()

        return instance

    def instantiate_object(self, data):
        invoice = super(InvoiceSerializer, self).instantiate_object(data)
        # after clean_defaults is moved into full_clean this call won't be needed
        invoice.clean_defaults()

        return invoice

    def validate(self, data):
        data = super(InvoiceSerializer, self).validate(data)

        if self.instance:
            self.instance.clean()

        if self.instance and data['state'] != self.instance.state:
            msg = "Direct state modification is not allowed." \
                  " Use the corresponding endpoint to update the state."
            raise serializers.ValidationError(msg)
        return data


class ProformaSerializer(AutoCleanSerializerMixin,
                         serializers.HyperlinkedModelSerializer):
    proforma_entries = DocumentEntrySerializer(many=True, required=False)
    pdf_url = PDFUrl(view_name='pdf', source='*', read_only=True)
    customer = CustomerUrl(view_name='customer-detail',
                           queryset=Customer.objects.all())
    transactions = TransactionSerializer(many=True, read_only=True)

    class Meta:
        model = Proforma
        fields = ('id', 'series', 'number', 'provider', 'customer',
                  'archived_provider', 'archived_customer', 'due_date',
                  'issue_date', 'paid_date', 'cancel_date', 'sales_tax_name',
                  'sales_tax_percent', 'currency', 'transaction_currency',
                  'transaction_xe_rate', 'transaction_xe_date', 'state', 'invoice',
                  'proforma_entries', 'total', 'total_in_transaction_currency',
                  'pdf_url', 'transactions')
        read_only_fields = ('archived_provider', 'archived_customer', 'total',
                            'total_in_transaction_currency')
        extra_kwargs = {
            'transaction_currency': {'required': False},
            'invoice': {'source': 'related_document', 'view_name': 'invoice-detail'},
        }

    def create(self, validated_data):
        entries = validated_data.pop('proforma_entries', [])

        proforma = Proforma.objects.create(**validated_data)

        for entry in entries:
            entry_dict = dict()
            entry_dict['proforma'] = proforma
            for field in entry.items():
                entry_dict[field[0]] = field[1]

            DocumentEntry.objects.create(**entry_dict)

        return proforma

    def update(self, instance, validated_data):
        # The provider has changed => force the generation of the correct number
        # corresponding to the count of the new provider
        current_provider = instance.provider
        new_provider = validated_data.get('provider')
        if new_provider and new_provider != current_provider:
            instance.number = None

        updateable_fields = instance.updateable_fields
        for field_name in updateable_fields:
            field_value = validated_data.get(field_name,
                                             getattr(instance, field_name))
            setattr(instance, field_name, field_value)
        instance.save()

        return instance

    def instantiate_object(self, data):
        proforma = super(ProformaSerializer, self).instantiate_object(data)
        # after clean_defaults is moved into full_clean this call won't be needed
        proforma.clean_defaults()

        return proforma

    def validate(self, data):
        data = super(ProformaSerializer, self).validate(data)

        if self.instance and data['state'] != self.instance.state:
            msg = "Direct state modification is not allowed." \
                  " Use the corresponding endpoint to update the state."
            raise serializers.ValidationError(msg)
        return data
