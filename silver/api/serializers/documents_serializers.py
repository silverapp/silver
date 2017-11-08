from rest_framework import serializers

# from silver.api.serializers import PDFUrl
from silver.api.serializers.common import CustomerUrl, PDFUrl
from silver.api.serializers.transaction_serializers import TransactionSerializer
from silver.models import DocumentEntry, Customer, Transaction, Invoice, Proforma
from silver.models.documents import Document


class DocumentEntrySerializer(serializers.HyperlinkedModelSerializer):
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
    pdf_url = PDFUrl(view_name='', source='*', read_only=True)
    url = DocumentUrl(proforma_view_name='proforma-detail',
                      invoice_view_name='invoice-detail', )

    transactions = serializers.SerializerMethodField()

    def get_transactions(self, document):
        transactions = None

        if document.kind == 'invoice':
            transactions = Transaction.objects.filter(invoice_id=document.id)\
                                              .select_related('payment_method')
        elif document.kind == 'proforma':
            transactions = Transaction.objects.filter(proforma_id=document.id)\
                                              .select_related('payment_method')

        for transaction in transactions:
            transaction.payment_method.customer = document.customer
            transaction.provider = document.provider

        return TransactionSerializer(transactions, many=True,
                                     context=self.context).data

    class Meta:
        model = Document
        fields = ('id', 'url', 'kind', 'series', 'number', 'provider',
                  'customer', 'due_date', 'issue_date', 'paid_date',
                  'cancel_date', 'sales_tax_name', 'sales_tax_percent',
                  'transaction_currency', 'currency', 'state', 'total',
                  'total_in_transaction_currency', 'pdf_url', 'transactions')
        read_only_fields = fields


class InvoiceSerializer(serializers.HyperlinkedModelSerializer):
    invoice_entries = DocumentEntrySerializer(many=True)
    pdf_url = PDFUrl(view_name='', source='*', read_only=True)
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
            'transaction_currency': {'required': False}
        }

    def create(self, validated_data):
        entries = validated_data.pop('invoice_entries', None)

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

    def validate(self, data):
        data = super(InvoiceSerializer, self).validate(data)

        if self.instance:
            self.instance.clean()

        if self.instance and data['state'] != self.instance.state:
            msg = "Direct state modification is not allowed." \
                  " Use the corresponding endpoint to update the state."
            raise serializers.ValidationError(msg)
        return data


class ProformaSerializer(serializers.HyperlinkedModelSerializer):
    proforma_entries = DocumentEntrySerializer(many=True)
    pdf_url = PDFUrl(view_name='', source='*', read_only=True)
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
            'transaction_currency': {'required': False}
        }

    def create(self, validated_data):
        entries = validated_data.pop('proforma_entries', None)

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

    def validate(self, data):
        data = super(ProformaSerializer, self).validate(data)

        if self.instance:
            self.instance.clean()

        if self.instance and data['state'] != self.instance.state:
            msg = "Direct state modification is not allowed." \
                  " Use the corresponding endpoint to update the state."
            raise serializers.ValidationError(msg)
        return data
