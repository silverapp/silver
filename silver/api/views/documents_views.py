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

from django_filters.rest_framework import DjangoFilterBackend

import django

from django.db.models import Q
from django.http import HttpResponseRedirect

from rest_framework import generics, permissions, filters, status
from rest_framework.generics import get_object_or_404, ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from silver.api.filters import InvoiceFilter, ProformaFilter, BillingDocumentFilter
from silver.api.serializers.documents_serializers import (
    InvoiceSerializer, DocumentEntrySerializer, ProformaSerializer, DocumentSerializer
)
from silver.models import Invoice, BillingDocumentBase, DocumentEntry, Proforma, PDF


class InvoiceListCreate(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = InvoiceSerializer
    queryset = Invoice.objects.all()\
        .select_related('related_document')\
        .prefetch_related('invoice_transactions')
    filter_backends = (DjangoFilterBackend,)
    filter_class = InvoiceFilter


class InvoiceRetrieveUpdate(generics.RetrieveUpdateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = InvoiceSerializer
    queryset = Invoice.objects.all()


class DocEntryCreate(generics.CreateAPIView):
    def get_model(self):
        raise NotImplementedError

    def get_model_name(self):
        raise NotImplementedError

    def post(self, request, *args, **kwargs):
        doc_pk = kwargs.get('document_pk')
        Model = self.get_model()
        model_name = self.get_model_name()

        try:
            document = Model.objects.get(pk=doc_pk)
        except Model.DoesNotExist:
            msg = "{model} not found".format(model=model_name)
            return Response({"detail": msg}, status=status.HTTP_404_NOT_FOUND)

        if document.state != BillingDocumentBase.STATES.DRAFT:
            msg = "{model} entries can be added only when the {model_lower} is"\
                  " in draft state.".format(model=model_name,
                                            model_lower=model_name.lower())
            return Response({"detail": msg}, status=status.HTTP_403_FORBIDDEN)

        serializer = DocumentEntrySerializer(data=request.data,
                                             context={'request': request})

        if serializer.is_valid(raise_exception=True):
            # This will be eiter {invoice: <invoice_object>} or
            # {proforma: <proforma_object>} as a DocumentEntry can have a
            # foreign key to either an invoice or a proforma
            extra_context = {model_name.lower(): document}
            serializer.save(**extra_context)

            return Response(serializer.data, status=status.HTTP_201_CREATED)


class InvoiceEntryCreate(DocEntryCreate):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = DocumentEntrySerializer
    queryset = DocumentEntry.objects.all()

    def post(self, request, *args, **kwargs):
        return super(InvoiceEntryCreate, self).post(request, *args, **kwargs)

    def get_model(self):
        return Invoice

    def get_model_name(self):
        return "Invoice"


class DocEntryUpdateDestroy(APIView):

    def put(self, request, *args, **kwargs):
        doc_pk = kwargs.get('document_pk')
        entry_pk = kwargs.get('entry_pk')

        Model = self.get_model()
        model_name = self.get_model_name()

        document = get_object_or_404(Model, pk=doc_pk)
        if document.state != BillingDocumentBase.STATES.DRAFT:
            msg = "{model} entries can be added only when the {model_lower} is"\
                  " in draft state.".format(model=model_name,
                                            model_lower=model_name.lower())
            return Response({"detail": msg}, status=status.HTTP_403_FORBIDDEN)

        searched_fields = {model_name.lower(): document, 'pk': entry_pk}
        entry = get_object_or_404(DocumentEntry, **searched_fields)

        serializer = DocumentEntrySerializer(entry, data=request.data,
                                             context={'request': request})

        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(serializer.data)

    def delete(self, request, *args, **kwargs):
        doc_pk = kwargs.get('document_pk')
        entry_pk = kwargs.get('entry_pk')

        Model = self.get_model()
        model_name = self.get_model_name()

        document = get_object_or_404(Model, pk=doc_pk)
        if document.state != BillingDocumentBase.STATES.DRAFT:
            msg = "{model} entries can be deleted only when the {model_lower} is"\
                  " in draft state.".format(model=model_name,
                                            model_lower=model_name.lower())
            return Response({"detail": msg}, status=status.HTTP_403_FORBIDDEN)

        searched_fields = {model_name.lower(): document, 'pk': entry_pk}
        entry = get_object_or_404(DocumentEntry, **searched_fields)
        entry.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_model(self):
        raise NotImplementedError

    def get_model_name(self):
        raise NotImplementedError


class InvoiceEntryUpdateDestroy(DocEntryUpdateDestroy):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = DocumentEntrySerializer
    queryset = DocumentEntry.objects.all()

    def put(self, request, *args, **kwargs):
        return super(InvoiceEntryUpdateDestroy, self).put(request, *args,
                                                          **kwargs)

    def delete(self, request, *args, **kwargs):
        return super(InvoiceEntryUpdateDestroy, self).delete(request, *args,
                                                             **kwargs)

    def get_model(self):
        return Invoice

    def get_model_name(self):
        return "Invoice"


class InvoiceStateHandler(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = InvoiceSerializer

    def put(self, request, *args, **kwargs):
        invoice_pk = kwargs.get('pk')
        try:
            invoice = Invoice.objects.get(pk=invoice_pk)
        except Invoice.DoesNotExist:
            return Response({"detail": "Invoice not found"},
                            status=status.HTTP_404_NOT_FOUND)

        state = request.data.get('state', None)
        if state == Invoice.STATES.ISSUED:
            if invoice.state != Invoice.STATES.DRAFT:
                msg = "An invoice can be issued only if it is in draft state."
                return Response({"detail": msg},
                                status=status.HTTP_403_FORBIDDEN)

            issue_date = request.data.get('issue_date', None)
            due_date = request.data.get('due_date', None)
            invoice.issue(issue_date, due_date)
        elif state == Invoice.STATES.PAID:
            if invoice.state != Invoice.STATES.ISSUED:
                msg = "An invoice can be paid only if it is in issued state."
                return Response({"detail": msg},
                                status=status.HTTP_403_FORBIDDEN)

            paid_date = request.data.get('paid_date', None)
            invoice.pay(paid_date)
        elif state == Invoice.STATES.CANCELED:
            if invoice.state != Invoice.STATES.ISSUED:
                msg = "An invoice can be canceled only if it is in issued " \
                      "state."
                return Response({"detail": msg},
                                status=status.HTTP_403_FORBIDDEN)

            cancel_date = request.data.get('cancel_date', None)
            invoice.cancel(cancel_date)
        elif not state:
            msg = "You have to provide a value for the state field."
            return Response({"detail": msg}, status=status.HTTP_403_FORBIDDEN)
        else:
            msg = "Illegal state value."
            return Response({"detail": msg}, status=status.HTTP_403_FORBIDDEN)

        serializer = InvoiceSerializer(invoice, context={'request': request})
        return Response(serializer.data)


class ProformaListCreate(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ProformaSerializer
    queryset = Proforma.objects.all()\
        .select_related('related_document')\
        .prefetch_related('proforma_transactions')
    filter_backends = (DjangoFilterBackend,)
    filter_class = ProformaFilter


class ProformaRetrieveUpdate(generics.RetrieveUpdateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ProformaSerializer
    queryset = Proforma.objects.all()


class ProformaEntryCreate(DocEntryCreate):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = DocumentEntrySerializer
    queryset = DocumentEntry.objects.all()

    def post(self, request, *args, **kwargs):
        return super(ProformaEntryCreate, self).post(request, *args, **kwargs)

    def get_model(self):
        return Proforma

    def get_model_name(self):
        return "Proforma"


class ProformaEntryUpdateDestroy(DocEntryUpdateDestroy):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = DocumentEntrySerializer
    queryset = DocumentEntry.objects.all()

    def put(self, request, *args, **kwargs):
        return super(ProformaEntryUpdateDestroy, self).put(request, *args,
                                                           **kwargs)

    def delete(self, request, *args, **kwargs):
        return super(ProformaEntryUpdateDestroy, self).delete(request, *args,
                                                              **kwargs)

    def get_model(self):
        return Proforma

    def get_model_name(self):
        return "Proforma"


class ProformaInvoiceRetrieveCreate(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = InvoiceSerializer

    def post(self, request, *args, **kwargs):
        proforma_pk = kwargs.get('pk')

        try:
            proforma = Proforma.objects.get(pk=proforma_pk)
        except Proforma.DoesNotExist:
            return Response({"detail": "Proforma not found"},
                            status=status.HTTP_404_NOT_FOUND)

        if not proforma.related_document:
            proforma.create_invoice()

        serializer = InvoiceSerializer(proforma.related_document,
                                       context={'request': request})
        return Response(serializer.data)

    def get(self, request, *args, **kwargs):
        proforma_pk = kwargs.get('pk')

        try:
            proforma = Proforma.objects.get(pk=proforma_pk)
        except Proforma.DoesNotExist:
            return Response({"detail": "Proforma not found"},
                            status=status.HTTP_404_NOT_FOUND)

        serializer = InvoiceSerializer(proforma.related_document,
                                       context={'request': request})
        return Response(serializer.data)


class ProformaStateHandler(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ProformaSerializer

    def put(self, request, *args, **kwargs):
        proforma_pk = kwargs.get('pk')
        try:
            proforma = Proforma.objects.get(pk=proforma_pk)
        except Proforma.DoesNotExist:
            return Response({"detail": "Proforma not found"},
                            status=status.HTTP_404_NOT_FOUND)

        state = request.data.get('state', None)
        if state == Proforma.STATES.ISSUED:
            if proforma.state != Proforma.STATES.DRAFT:
                msg = "A proforma can be issued only if it is in draft state."
                return Response({"detail": msg},
                                status=status.HTTP_403_FORBIDDEN)

            issue_date = request.data.get('issue_date', None)
            due_date = request.data.get('due_date', None)
            proforma.issue(issue_date, due_date)
        elif state == Proforma.STATES.PAID:
            if proforma.state != Proforma.STATES.ISSUED:
                msg = "A proforma can be paid only if it is in issued state."
                return Response({"detail": msg},
                                status=status.HTTP_403_FORBIDDEN)

            paid_date = request.data.get('paid_date', None)
            proforma.pay(paid_date)
        elif state == Proforma.STATES.CANCELED:
            if proforma.state != Proforma.STATES.ISSUED:
                msg = "A proforma can be canceled only if it is in issued " \
                      "state."
                return Response({"detail": msg},
                                status=status.HTTP_403_FORBIDDEN)

            cancel_date = request.data.get('cancel_date', None)
            proforma.cancel(cancel_date)
        elif not state:
            msg = "You have to provide a value for the state field."
            return Response({"detail": msg}, status=status.HTTP_403_FORBIDDEN)
        else:
            msg = "Illegal state value."
            return Response({"detail": msg}, status=status.HTTP_403_FORBIDDEN)

        serializer = ProformaSerializer(proforma, context={'request': request})
        return Response(serializer.data)


class DocumentList(ListAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = DocumentSerializer
    filter_class = BillingDocumentFilter
    filter_backends = (filters.OrderingFilter, DjangoFilterBackend)
    ordering_fields = ('due_date', )
    ordering = ('-due_date', '-number')

    def get_queryset(self):
        django_version = django.get_version().split('.')
        if django_version[0] == '1' and int(django_version[1]) < 11:
            return BillingDocumentBase.objects.filter(
                Q(kind='invoice') | Q(kind='proforma', related_document=None)
            ).select_related('customer', 'provider', 'pdf')

        invoices = BillingDocumentBase.objects \
            .filter(kind='invoice') \
            .prefetch_related('invoice_transactions__payment_method')
        proformas = BillingDocumentBase.objects \
            .filter(kind='proforma', related_document=None) \
            .prefetch_related('proforma_transactions__payment_method')

        return (invoices | proformas).select_related('customer', 'provider', 'pdf')


class PDFRetrieve(generics.RetrieveAPIView):
    permission_classes = (permissions.IsAdminUser,)
    queryset = PDF.objects.all()
    lookup_url_kwarg = 'pdf_pk'

    def get(self, *args, **kwargs):
        pdf = self.get_object()
        return HttpResponseRedirect(pdf.url)
