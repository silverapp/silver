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


import datetime
import logging
from decimal import Decimal
from uuid import UUID

from django_fsm import TransitionNotAllowed
from annoying.functions import get_object_or_None

from django.utils import timezone
from django.http.response import Http404

from rest_framework import generics, permissions, status, filters
from rest_framework.generics import (get_object_or_404, ListCreateAPIView,
                                     RetrieveUpdateAPIView, ListAPIView,
                                     RetrieveAPIView)
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView
from rest_framework_bulk import ListBulkCreateAPIView

from silver.models import (MeteredFeatureUnitsLog, Subscription, MeteredFeature,
                           Customer, Plan, Provider, Invoice, ProductCode,
                           DocumentEntry, Proforma, BillingDocumentBase,
                           PaymentMethod, Transaction)
from silver.models.documents.document import Document
from silver.api.serializers import (MFUnitsLogSerializer,
                                    CustomerSerializer, SubscriptionSerializer,
                                    SubscriptionDetailSerializer,
                                    PlanSerializer, MeteredFeatureSerializer,
                                    ProviderSerializer, InvoiceSerializer,
                                    ProductCodeSerializer, ProformaSerializer,
                                    DocumentEntrySerializer,
                                    PaymentProcessorSerializer,
                                    PaymentMethodSerializer,
                                    TransactionSerializer, DocumentSerializer)
from silver.api.filters import (MeteredFeaturesFilter, SubscriptionFilter,
                                CustomerFilter, ProviderFilter, PlanFilter,
                                InvoiceFilter, ProformaFilter,
                                PaymentMethodFilter, TransactionFilter,
                                DocumentFilter)
from silver import payment_processors

logger = logging.getLogger(__name__)


class PlanList(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = PlanSerializer
    queryset = Plan.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = PlanFilter


class PlanDetail(generics.RetrieveDestroyAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = PlanSerializer
    model = Plan

    def get_object(self):
        pk = self.kwargs.get('pk', None)
        return get_object_or_404(Plan, pk=pk)

    def patch(self, request, *args, **kwargs):
        plan = get_object_or_404(Plan.objects, pk=self.kwargs.get('pk', None))
        name = request.data.get('name', None)
        generate_after = request.data.get('generate_after', None)
        plan.name = name or plan.name
        plan.generate_after = generate_after or plan.generate_after
        plan.save()
        return Response(PlanSerializer(plan, context={'request': request}).data,
                        status=status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        plan = get_object_or_404(Plan.objects, pk=self.kwargs.get('pk', None))
        plan.enabled = False
        plan.save()
        return Response({"deleted": not plan.enabled},
                        status=status.HTTP_200_OK)


class PlanMeteredFeatures(generics.ListAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = MeteredFeatureSerializer
    model = MeteredFeature

    def get_queryset(self):
        plan = get_object_or_None(Plan, pk=self.kwargs['pk'])
        return plan.metered_features.all() if plan else None


class MeteredFeatureList(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = MeteredFeatureSerializer
    queryset = MeteredFeature.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = MeteredFeaturesFilter


class MeteredFeatureDetail(generics.RetrieveAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = MeteredFeatureSerializer
    model = MeteredFeature

    def get_object(self):
        customer_pk = self.kwargs.get('pk', None)
        return get_object_or_404(MeteredFeature, pk=customer_pk)


class SubscriptionList(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = SubscriptionSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = SubscriptionFilter

    def get_queryset(self):
        customer_pk = self.kwargs.get('customer_pk', None)
        queryset = Subscription.objects.filter(customer__pk=customer_pk)
        return queryset.order_by('start_date')

    def post(self, request, *args, **kwargs):
        customer_pk = self.kwargs.get('customer_pk', None)
        url = reverse('customer-detail', kwargs={'customer_pk': customer_pk},
                      request=request)
        request.data.update({unicode('customer'): unicode(url)})

        return super(SubscriptionList, self).post(request, *args, **kwargs)


class SubscriptionDetail(generics.RetrieveUpdateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = SubscriptionDetailSerializer

    def get_object(self):
        customer_pk = self.kwargs.get('customer_pk', None)
        subscription_pk = self.kwargs.get('subscription_pk', None)
        return get_object_or_404(Subscription, customer__id=customer_pk,
                                 pk=subscription_pk)

    def put(self, request, *args, **kwargs):
        return Response({'detail': 'Method "PUT" not allowed.'},
                        status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def patch(self, request, *args, **kwargs):
        sub = get_object_or_404(Subscription.objects,
                                pk=self.kwargs.get('subscription_pk', None))
        state = sub.state
        meta = request.data.pop('meta', None)
        if request.data:
            message = "Cannot update a subscription when it's in %s state." \
                      % state
            return Response({"detail": message},
                            status=status.HTTP_400_BAD_REQUEST)
        request.data.clear()
        request.data.update({'meta': meta} if meta else {})
        return super(SubscriptionDetail, self).patch(request,
                                                     *args, **kwargs)


class SubscriptionActivate(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        sub = get_object_or_404(Subscription.objects,
                                pk=self.kwargs.get('subscription_pk', None))
        if sub.state != Subscription.STATES.INACTIVE:
            message = 'Cannot activate subscription from %s state.' % sub.state
            return Response({"error": message},
                            status=status.HTTP_400_BAD_REQUEST)
        else:
            if request.POST.get('_content', None):
                start_date = request.data.get('start_date', None)
                trial_end = request.data.get('trial_end_date', None)
                if start_date:
                    try:
                        start_date = datetime.datetime.strptime(
                            start_date, '%Y-%m-%d').date()
                    except TypeError:
                        return Response(
                            {'detail': 'Invalid start_date date format. Please '
                                       'use the ISO 8601 date format.'},
                            status=status.HTTP_400_BAD_REQUEST)
                if trial_end:
                    try:
                        trial_end = datetime.datetime.strptime(
                            trial_end, '%Y-%m-%d').date()
                    except TypeError:
                        return Response(
                            {'detail': 'Invalid trial_end date format. Please '
                                       'use the ISO 8601 date format.'},
                            status=status.HTTP_400_BAD_REQUEST)
                sub.activate(start_date=start_date, trial_end_date=trial_end)
                sub.save()
            else:
                sub.activate()
                sub.save()

            logger.debug('Activated subscription: %s', {
                'subscription': sub.id,
                'date': timezone.now().date().strftime('%Y-%m-%d')
            })

            return Response({"state": sub.state},
                            status=status.HTTP_200_OK)


class SubscriptionCancel(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        sub = get_object_or_404(Subscription,
                                pk=kwargs.get('subscription_pk', None))
        when = request.data.get('when', None)
        if sub.state != Subscription.STATES.ACTIVE:
            message = 'Cannot cancel subscription from %s state.' % sub.state
            return Response({"error": message},
                            status=status.HTTP_400_BAD_REQUEST)
        else:
            if when in [Subscription.CANCEL_OPTIONS.NOW,
                        Subscription.CANCEL_OPTIONS.END_OF_BILLING_CYCLE]:
                sub.cancel(when=when)
                sub.save()

                logger.debug('Canceled subscription: %s', {
                    'subscription': sub.id,
                    'date': timezone.now().date().strftime('%Y-%m-%d'),
                    'when': when,
                })

                return Response({"state": sub.state},
                                status=status.HTTP_200_OK)
            else:
                if when is None:
                    err = 'You must provide the `when` argument'
                    return Response({'error': err},
                                    status=status.HTTP_400_BAD_REQUEST)
                else:
                    err = 'You must provide a correct value for the `when` argument'
                    return Response({'error': err},
                                    status=status.HTTP_400_BAD_REQUEST)


class SubscriptionReactivate(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        sub = get_object_or_404(Subscription,
                                pk=kwargs.get('subscription_pk', None))
        if sub.state != Subscription.STATES.CANCELED:
            msg = 'Cannot reactivate subscription from %s state.' % sub.state
            return Response({"error": msg},
                            status=status.HTTP_400_BAD_REQUEST)
        else:
            sub.activate()
            sub.save()

            logger.debug('Reactivated subscription: %s', {
                'subscription': sub.id,
                'date': timezone.now().date().strftime('%Y-%m-%d'),
            })

            return Response({"state": sub.state},
                            status=status.HTTP_200_OK)


class MeteredFeatureUnitsLogDetail(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    paginate_by = None

    def get(self, request, format=None, **kwargs):
        subscription_pk = kwargs.get('subscription_pk', None)
        mf_product_code = kwargs.get('mf_product_code', None)

        subscription = Subscription.objects.get(pk=subscription_pk)

        metered_feature = get_object_or_404(
            subscription.plan.metered_features,
            product_code__value=mf_product_code
        )

        logs = MeteredFeatureUnitsLog.objects.filter(
            metered_feature=metered_feature.pk,
            subscription=subscription_pk)

        serializer = MFUnitsLogSerializer(
            logs, many=True, context={'request': request}
        )
        return Response(serializer.data)

    def patch(self, request, *args, **kwargs):
        mf_product_code = self.kwargs.get('mf_product_code', None)
        subscription_pk = self.kwargs.get('subscription_pk', None)

        try:
            subscription = Subscription.objects.get(pk=subscription_pk)
        except Subscription.DoesNotExist:
            return Response({"detail": "Subscription Not found."},
                            status=status.HTTP_404_NOT_FOUND)

        # TODO: change this to try-except
        metered_feature = get_object_or_None(
            subscription.plan.metered_features,
            product_code__value=mf_product_code
        )

        if not metered_feature:
            return Response({"detail": "Metered Feature Not found."},
                            status=status.HTTP_404_NOT_FOUND)

        if subscription.state != 'active':
            return Response({"detail": "Subscription is not active."},
                            status=status.HTTP_403_FORBIDDEN)

        required_fields = ['date', 'count', 'update_type']
        provided_fields = {}
        errors = {}
        for field in required_fields:
            try:
                provided_fields[field] = request.data[field]
            except KeyError:
                errors[field] = ["This field is required."]

        for key in provided_fields:
            if not provided_fields[key]:
                errors[key] = ["This field may not be blank."]

        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        date = request.data['date']
        consumed_units = request.data['count']
        update_type = request.data['update_type']

        consumed_units = Decimal(consumed_units)

        try:
            date = datetime.datetime.strptime(date,
                                              '%Y-%m-%d').date()
        except TypeError:
            return Response({'detail': 'Invalid date format. Please '
                            'use the ISO 8601 date format.'},
                            status=status.HTTP_400_BAD_REQUEST)

        if date < subscription.start_date:
            return Response({"detail": "Date is out of bounds."},
                            status=status.HTTP_400_BAD_REQUEST)

        bsd = subscription.bucket_start_date(date)
        bed = subscription.bucket_end_date(date)
        if not bsd or not bed:
            return Response(
                {'detail': 'An error has been encountered.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        interval = next(
            (i for i in subscription.updateable_buckets()
                if i['start_date'] == bsd and i['end_date'] == bed),
            None)

        if interval is None:
            return Response({"detail": "Date is out of bounds."},
                            status=status.HTTP_400_BAD_REQUEST)

        if metered_feature not in \
                subscription.plan.metered_features.all():
            err = "The metered feature does not belong to the " \
                  "subscription's plan."
            return Response(
                {"detail": err},
                status=status.HTTP_400_BAD_REQUEST
            )

        log = MeteredFeatureUnitsLog.objects.filter(
            start_date=bsd,
            end_date=bed,
            metered_feature=metered_feature.pk,
            subscription=subscription_pk
        ).first()

        if log is not None:
            if update_type == 'absolute':
                log.consumed_units = consumed_units
            elif update_type == 'relative':
                log.consumed_units += consumed_units
            log.save()
        else:
            log = MeteredFeatureUnitsLog.objects.create(
                metered_feature=metered_feature,
                subscription=subscription,
                start_date=bsd,
                end_date=bed,
                consumed_units=consumed_units
            )
        return Response({"count": log.consumed_units},
                        status=status.HTTP_200_OK)


class CustomerList(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = CustomerSerializer
    queryset = Customer.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = CustomerFilter


class CustomerDetail(generics.RetrieveUpdateDestroyAPIView):
    def get_object(self):
        pk = self.kwargs.get('customer_pk', None)
        try:
            return Customer.objects.get(pk=pk)
        except (TypeError, ValueError, Customer.DoesNotExist):
            raise Http404

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = CustomerSerializer
    model = Customer


class ProductCodeListCreate(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ProductCodeSerializer
    queryset = ProductCode.objects.all()


class ProductCodeRetrieveUpdate(generics.RetrieveUpdateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ProductCodeSerializer
    queryset = ProductCode.objects.all()


class ProviderListCreate(ListBulkCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ProviderSerializer
    queryset = Provider.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = ProviderFilter


class ProviderRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ProviderSerializer
    queryset = Provider.objects.all()


class InvoiceListCreate(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = InvoiceSerializer
    queryset = Invoice.objects.all()\
        .select_related('proforma')\
        .prefetch_related('transaction_set')
    filter_backends = (filters.DjangoFilterBackend,)
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
        .select_related('invoice')\
        .prefetch_related('transaction_set')
    filter_backends = (filters.DjangoFilterBackend,)
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

        if not proforma.invoice:
            proforma.create_invoice()

        serializer = InvoiceSerializer(proforma.invoice,
                                       context={'request': request})
        return Response(serializer.data)

    def get(self, request, *args, **kwargs):
        proforma_pk = kwargs.get('pk')

        try:
            proforma = Proforma.objects.get(pk=proforma_pk)
        except Proforma.DoesNotExist:
            return Response({"detail": "Proforma not found"},
                            status=status.HTTP_404_NOT_FOUND)

        serializer = InvoiceSerializer(proforma.invoice,
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
    filter_class = DocumentFilter
    filter_backends = (filters.OrderingFilter, filters.DjangoFilterBackend)
    ordering_fields = ('due_date', )
    ordering = ('-due_date', '-number')

    def get_queryset(self):
        return Document.objects.all().select_related('provider', 'customer')


class PaymentProcessorList(ListAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = PaymentProcessorSerializer
    ordering = ('-name', )

    def get_queryset(self):
        return payment_processors.get_all_instances()


class PaymentProcessorDetail(RetrieveAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = PaymentProcessorSerializer
    ordering = ('-name', )

    def get_object(self):
        processor_name = self.kwargs.get('processor_name', '')
        try:
            return payment_processors.get_instance(processor_name)
        except (ImportError, KeyError):
            raise Http404


class PaymentMethodList(ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = PaymentMethodSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = PaymentMethodFilter

    def get_queryset(self):
        return PaymentMethod.objects.filter(customer=self.customer)

    def get_customer(self, request):
        context = self.get_parser_context(request)
        kwargs = context['kwargs']

        customer_pk = kwargs.get('customer_pk', None)

        return get_object_or_404(Customer, id=customer_pk)

    def list(self, request, *args, **kwargs):
        customer = self.get_customer(request)

        self.customer = customer

        return super(PaymentMethodList, self).list(request, *args, **kwargs)

    def perform_create(self, serializer):
        customer = self.get_customer(self.request)
        serializer.save(customer=customer)


class PaymentMethodDetail(RetrieveUpdateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = PaymentMethodSerializer

    def get_object(self):
        payment_method_id = self.kwargs.get('payment_method_id')
        customer_pk = self.kwargs.get('customer_pk')

        return get_object_or_404(
            PaymentMethod.objects.all().select_subclasses(),
            id=payment_method_id,
            customer__pk=customer_pk
        )


class PaymentMethodAction(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    allowed_actions = ('cancel', )

    def post(self, request, *args, **kwargs):
        payment_method = self.get_object(**kwargs)
        requested_action = kwargs.get('requested_action')

        if requested_action not in self.allowed_actions:
            error_message = "{} is not an allowed".format(requested_action)
            return Response({"errors": error_message},
                            status=status.HTTP_400_BAD_REQUEST)

        action_to_execute = getattr(payment_method, requested_action, None)

        if not action_to_execute:
            raise Http404

        errors = action_to_execute()
        if errors:
            return Response({"errors": errors},
                            status=status.HTTP_400_BAD_REQUEST)

        payment_method_serialized = PaymentMethodSerializer(payment_method,
                                                            context={'request': request})
        return Response(payment_method_serialized.data,
                        status=status.HTTP_200_OK)

    def get_object(self, **kwargs):
        payment_method_id = kwargs.get('payment_method_id')
        customer_pk = kwargs.get('customer_pk')

        return get_object_or_404(
            PaymentMethod.objects.all().select_subclasses(),
            id=payment_method_id,
            customer__pk=customer_pk
        )


class TransactionList(ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = TransactionSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = TransactionFilter

    def get_queryset(self):
        customer_pk = self.kwargs.get('customer_pk', None)

        payment_method_id = self.kwargs.get('payment_method_id')
        if payment_method_id:
            payment_method = get_object_or_404(PaymentMethod,
                                               id=payment_method_id,
                                               customer__pk=customer_pk)

            return Transaction.objects.filter(
                payment_method=payment_method
            )
        else:
            return Transaction.objects.filter(
                payment_method__customer__pk=customer_pk
            )

    def perform_create(self, serializer):
        payment_method_id = self.kwargs.get('payment_method_id')
        if payment_method_id:
            payment_method = get_object_or_404(PaymentMethod,
                                               id=payment_method_id)
            serializer.save(payment_method=payment_method)
        else:
            serializer.save()


class TransactionDetail(RetrieveUpdateAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = TransactionSerializer
    http_method_names = ('get', 'patch', 'head', 'options')

    def get_object(self):
        transaction_uuid = self.kwargs.get('transaction_uuid', None)
        try:
            uuid = UUID(transaction_uuid, version=4)
        except ValueError:
            raise Http404

        return get_object_or_404(Transaction, uuid=uuid)


class TransactionAction(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    allowed_actions = ('cancel', )

    def post(self, request, *args, **kwargs):
        transaction = self.get_object(**kwargs)
        requested_action = kwargs.get('requested_action')

        if requested_action not in self.allowed_actions:
            error_message = "{} is not an allowed".format(requested_action)
            return Response({"errors": error_message},
                            status=status.HTTP_400_BAD_REQUEST)

        action_to_execute = getattr(transaction, requested_action, None)
        if not action_to_execute:
            raise Http404

        try:
            errors = action_to_execute()
            transaction.save()
        except TransitionNotAllowed:
            errors = "Can't execute action because the transaction is in an " \
                     "incorrect state: {}".format(transaction.state)

        if errors:
            return Response({"errors": errors},
                            status=status.HTTP_400_BAD_REQUEST)

        transaction_serialized = TransactionSerializer(transaction,
                                                       context={'request': request})
        return Response(transaction_serialized.data,
                        status=status.HTTP_200_OK)

    def get_object(self, **kwargs):
        transaction_uuid = kwargs.get('transaction_uuid')
        customer_pk = kwargs.get('customer_pk')

        return get_object_or_404(
            Transaction.objects.all(),
            uuid=transaction_uuid,
            payment_method__customer__pk=customer_pk
        )
