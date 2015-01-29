import datetime
from decimal import Decimal

from django.http.response import Http404
from django_filters import FilterSet, CharFilter, BooleanFilter
from rest_framework import generics, permissions, status, filters
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from silver.models import (MeteredFeatureUnitsLog, Subscription, MeteredFeature,
                           Customer, Plan, Provider, Invoice, ProductCode,
                           DocumentEntry, Proforma)
from silver.api.serializers import (MeteredFeatureUnitsLogSerializer,
                                    CustomerSerializer, SubscriptionSerializer,
                                    SubscriptionDetailSerializer,
                                    PlanSerializer, MeteredFeatureSerializer,
                                    ProviderSerializer, InvoiceSerializer,
                                    ProductCodeSerializer, ProformaSerializer,
                                    DocumentEntrySerializer)
from silver.api.generics import (HPListAPIView, HPListCreateAPIView)
from silver.utils import get_object_or_None
from silver.api.dateutils import last_date_that_fits


class PlanFilter(FilterSet):
    name = CharFilter(name='name', lookup_type='icontains')
    currency = CharFilter(name='currency', lookup_type='icontains')
    enabled = BooleanFilter(name='enabled', lookup_type='iexact')
    private = BooleanFilter(name='private', lookup_type='iexact')
    interval = CharFilter(name='interval', lookup_type='icontains')
    product_code = CharFilter(name='product_code', lookup_type='icontains')
    provider = CharFilter(name='provider__company', lookup_type='icontains')

    class Meta:
        model = Plan
        fields = ['name', 'currency', 'enabled', 'private', 'product_code',
                  'currency', 'provider', 'interval']


class PlanList(HPListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
    serializer_class = PlanSerializer
    queryset = Plan.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = PlanFilter


class PlanDetail(generics.RetrieveDestroyAPIView):
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
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


class PlanMeteredFeatures(HPListAPIView):
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
    serializer_class = MeteredFeatureSerializer
    model = MeteredFeature

    def get_queryset(self):
        plan = get_object_or_None(Plan, pk=self.kwargs['pk'])
        return plan.metered_features.all() if plan else None


class MeteredFeaturesFilter(FilterSet):
    name = CharFilter(name='name', lookup_type='icontains')

    class Meta:
        model = MeteredFeature
        fields = ('name', )


class MeteredFeatureList(HPListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
    serializer_class = MeteredFeatureSerializer
    queryset = MeteredFeature.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = MeteredFeaturesFilter


class MeteredFeatureDetail(generics.RetrieveAPIView):
    def get_object(self):
        pk = self.kwargs.get('pk', None)
        return get_object_or_404(MeteredFeature, pk=pk)

    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
    serializer_class = MeteredFeatureSerializer
    model = MeteredFeature


class SubscriptionFilter(FilterSet):
    plan = CharFilter(name='plan__name', lookup_type='icontains')
    customer = CharFilter(name='customer__name', lookup_type='icontains')
    company = CharFilter(name='customer__company', lookup_type='icontains')
    state = CharFilter(name='state', lookup_type='icontains')

    class Meta:
        model = Subscription
        fields = ['plan', 'customer', 'company', 'state']


class SubscriptionList(HPListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = SubscriptionFilter


class SubscriptionDetail(generics.RetrieveAPIView):
    def get_object(self):
        pk = self.kwargs.get('pk', None)
        return get_object_or_404(Subscription, pk=pk)

    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
    model = Subscription
    serializer_class = SubscriptionDetailSerializer


class SubscriptionDetailActivate(APIView):
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)

    def post(self, request, *args, **kwargs):
        sub = get_object_or_404(Subscription.objects,
                                pk=self.kwargs.get('sub', None))
        if sub.state != 'inactive':
            message = 'Cannot activate subscription from %s state.' % sub.state
            return Response({"error": message},
                            status=status.HTTP_400_BAD_REQUEST)
        else:
            if request.POST.get('_content', None):
                start_date = request.data.get('start_date', None)
                trial_end = request.data.get('trial_end_date', None)
                sub.activate(start_date=start_date, trial_end_date=trial_end)
                sub.save()
            else:
                sub.activate()
                sub.save()
            return Response({"state": sub.state},
                            status=status.HTTP_200_OK)


class SubscriptionDetailCancel(APIView):
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)

    def post(self, request, *args, **kwargs):
        sub = get_object_or_404(Subscription.objects,
                                pk=self.kwargs.get('sub', None))
        when = request.data.get('when', None)
        if sub.state != 'active':
            message = 'Cannot cancel subscription from %s state.' % sub.state
            return Response({"error": message},
                            status=status.HTTP_400_BAD_REQUEST)
        else:
            if when == 'now':
                sub.cancel()
                sub.end()
                sub.save()
                return Response({"state": sub.state},
                                status=status.HTTP_200_OK)
            elif when == 'end_of_billing_cycle':
                sub.cancel()
                sub.save()
                return Response({"state": sub.state},
                                status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_400_BAD_REQUEST)


class SubscriptionDetailReactivate(APIView):
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)

    def post(self, request, *args, **kwargs):
        sub = get_object_or_404(Subscription.objects,
                                pk=self.kwargs.get('sub', None))
        if sub.state != 'canceled':
            msg = 'Cannot reactivate subscription from %s state.' % sub.state
            return Response({"error": msg},
                            status=status.HTTP_400_BAD_REQUEST)
        else:
            sub.activate()
            sub.save()
            return Response({"state": sub.state},
                            status=status.HTTP_200_OK)


class MeteredFeatureUnitsLogList(APIView):
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
    paginate_by = None

    def get(self, request, format=None, **kwargs):
        metered_feature_pk = kwargs.get('mf', None)
        subscription_pk = kwargs.get('sub', None)
        logs = MeteredFeatureUnitsLog.objects.filter(
            metered_feature=metered_feature_pk,
            subscription=subscription_pk)
        serializer = MeteredFeatureUnitsLogSerializer(
            logs, many=True, context={'request': request}
        )
        return Response(serializer.data)

    def patch(self, request, *args, **kwargs):
        metered_feature_pk = self.kwargs['mf']
        subscription_pk = self.kwargs['sub']
        date = request.data.get('date', None)
        consumed_units = Decimal(request.data.get('count', 0))
        update_type = request.data.get('update_type', None)
        if subscription_pk and metered_feature_pk:
            subscription = get_object_or_None(Subscription, pk=subscription_pk)
            metered_feature = get_object_or_None(MeteredFeature,
                                                 pk=metered_feature_pk)

            if subscription and metered_feature:
                if subscription.state != 'active':
                    return Response({"detail": "Subscription is not active"},
                                    status=status.HTTP_403_FORBIDDEN)
                if date and consumed_units and update_type:
                    try:
                        date = datetime.datetime.strptime(date,
                                                          '%Y-%m-%d').date()
                        csd = subscription.current_start_date
                        ced = subscription.current_end_date

                        if date <= csd:
                            csdt = datetime.datetime.combine(csd, datetime.time())
                            allowed_time = datetime.timedelta(
                                seconds=subscription.plan.generate_after)
                            if datetime.datetime.now() < csdt + allowed_time:
                                ced = csd - datetime.timedelta(days=1)
                                csd = last_date_that_fits(
                                    initial_date=subscription.start_date,
                                    end_date=ced,
                                    interval_type=subscription.plan.interval,
                                    interval_count=subscription.plan.interval_count
                                )

                        if csd <= date <= ced:
                            if metered_feature not in \
                                    subscription.plan.metered_features.all():
                                err = "The metered feature does not belong to "\
                                      "the subscription's plan."
                                return Response(
                                    {"detail": err},
                                    status=status.HTTP_400_BAD_REQUEST
                                )
                            try:
                                log = MeteredFeatureUnitsLog.objects.get(
                                    start_date=csd,
                                    end_date=ced,
                                    metered_feature=metered_feature_pk,
                                    subscription=subscription_pk
                                )
                                if update_type == 'absolute':
                                    log.consumed_units = consumed_units
                                elif update_type == 'relative':
                                    log.consumed_units += consumed_units
                                log.save()
                            except MeteredFeatureUnitsLog.DoesNotExist:
                                log = MeteredFeatureUnitsLog.objects.create(
                                    metered_feature=metered_feature,
                                    subscription=subscription,
                                    start_date=subscription.current_start_date,
                                    end_date=subscription.current_end_date,
                                    consumed_units=consumed_units
                                )
                            finally:
                                return Response({"count": log.consumed_units},
                                                status=status.HTTP_200_OK)
                        else:
                            return Response({"detail": "Date is out of bounds"},
                                            status=status.HTTP_400_BAD_REQUEST)
                    except TypeError:
                        return Response({"detail": "Invalid date format"},
                                        status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({"detail": "Not enough information provided"},
                                    status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"detail": "Not found"},
                                status=status.HTTP_404_NOT_FOUND)
        return Response({"detail": "Wrong address"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CustomerFilter(FilterSet):
    active = BooleanFilter(name='is_active', lookup_type='iexact')
    email = CharFilter(name='email', lookup_type='icontains')
    company = CharFilter(name='company', lookup_type='icontains')
    name = CharFilter(name='name', lookup_type='icontains')
    country = CharFilter(name='country', lookup_type='icontains')
    sales_tax_name = CharFilter(name='sales_tax_name', lookup_type='icontains')

    class Meta:
        model = Customer
        fields = ['email', 'name', 'company', 'active', 'country',
                  'sales_tax_name']


class CustomerList(HPListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
    serializer_class = CustomerSerializer
    queryset = Customer.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = CustomerFilter


class CustomerDetail(generics.RetrieveUpdateDestroyAPIView):
    def get_object(self):
        pk = self.kwargs.get('pk', None)
        try:
            return Customer.objects.get(pk=pk)
        except (TypeError, ValueError, Customer.DoesNotExist):
            raise Http404

    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
    serializer_class = CustomerSerializer
    model = Customer


class ProviderFilter(FilterSet):
    email = CharFilter(name='email', lookup_type='icontains')
    company = CharFilter(name='company', lookup_type='icontains')

    class Meta:
        model = Provider
        fields = ['email', 'company']


class ProductCodeListCreate(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
    serializer_class = ProductCodeSerializer
    queryset = ProductCode.objects.all()


class ProductCodeRetrieveUpdate(generics.RetrieveUpdateAPIView):
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
    serializer_class = ProductCodeSerializer
    queryset = ProductCode.objects.all()


class ProviderListCreate(HPListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
    serializer_class = ProviderSerializer
    queryset = Provider.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = ProviderFilter


class ProviderRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
    serializer_class = ProviderSerializer
    queryset = Provider.objects.all()


class InvoiceListCreate(HPListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
    serializer_class = InvoiceSerializer
    queryset = Invoice.objects.all()


class InvoiceRetrieveUpdate(generics.RetrieveUpdateAPIView):
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
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

        if document.state != 'draft':
            msg = "{model} entries can be added only when the {model_lower} is"\
                  " in draft state.".format(model=model_name,
                                            model_lower=model_name.lower())
            return Response({"detail": msg}, status=status.HTTP_403_FORBIDDEN)

        serializer = DocumentEntrySerializer(data=request.DATA,
                                             context={'request': request})

        if serializer.is_valid(raise_exception=True):
            # This will be eiter {invoice: <invoice_object>} or
            # {proforma: <proforma_object>} as a DocumentEntry can have a
            # foreign key to either an invoice or a proforma
            extra_context = {model_name.lower(): document}
            serializer.save(**extra_context)

            return Response(serializer.data, status=status.HTTP_201_CREATED)


class InvoiceEntryCreate(DocEntryCreate):
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
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
        entry_id = kwargs.get('entry_id')

        Model = self.get_model()
        model_name = self.get_model_name()

        document = get_object_or_404(Model, pk=doc_pk)
        if document.state != 'draft':
            msg = "{model} entries can be added only when the {model_lower} is"\
                  " in draft state.".format(model=model_name,
                                            model_lower=model_name.lower())
            return Response({"detail": msg}, status=status.HTTP_403_FORBIDDEN)

        searched_fields = {model_name.lower(): document, 'entry_id': entry_id}
        entry = get_object_or_404(DocumentEntry, **searched_fields)

        serializer = DocumentEntrySerializer(entry, data=request.DATA,
                                             context={'request': request})

        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(serializer.data)

    def delete(self, request, *args, **kwargs):
        doc_pk = kwargs.get('document_pk')
        entry_id = kwargs.get('entry_id')

        Model = self.get_model()
        model_name = self.get_model_name()

        document = get_object_or_404(Model, pk=doc_pk)
        if document.state != 'draft':
            msg = "{model} entries can be added only when the {model_lower} is"\
                  " in draft state.".format(model=model_name,
                                            model_lower=model_name.lower())
            return Response({"detail": msg}, status=status.HTTP_403_FORBIDDEN)

        searched_fields = {model_name.lower(): document, 'entry_id': entry_id}
        entry = get_object_or_404(DocumentEntry, **searched_fields)
        entry.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_model(self):
        raise NotImplementedError

    def get_model_name(self):
        raise NotImplementedError

class InvoiceEntryUpdateDestroy(DocEntryUpdateDestroy):
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
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
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
    serializer_class = InvoiceSerializer

    def patch(self, request, *args, **kwargs):
        invoice_pk = kwargs.get('pk')
        try:
            invoice = Invoice.objects.get(pk=invoice_pk)
        except Invoice.DoesNotExist:
            return Response({"detail": "Invoice not found"},
                            status=status.HTTP_404_NOT_FOUND)

        state = request.DATA.get('state', None)
        if state == 'issued':
            if invoice.state != 'draft':
                msg = "An invoice can be issued only if it is in draft state."
                return Response({"detail": msg}, status=status.HTTP_403_FORBIDDEN)

            issue_date = request.DATA.get('issue_date', None)
            due_date = request.DATA.get('due_date', None)
            invoice.issue(issue_date, due_date)
            invoice.save()
        elif state == 'paid':
            if invoice.state != 'issued':
                msg = "An invoice can be paid only if it is in issued state."
                return Response({"detail": msg}, status=status.HTTP_403_FORBIDDEN)

            paid_date = request.DATA.get('paid_date', None)
            invoice.pay(paid_date)
            invoice.save()
        elif state == 'canceled':
            if invoice.state != 'issued':
                msg = "An invoice can be canceled only if it is in issued state."
                return Response({"detail": msg}, status=status.HTTP_403_FORBIDDEN)

            cancel_date = request.DATA.get('cancel_date', None)
            invoice.cancel(cancel_date)
            invoice.save()
        elif not state:
            msg = "You have to provide a value for the state field."
            return Response({"detail": msg}, status=status.HTTP_403_FORBIDDEN)
        else:
            msg = "Illegal state value."
            return Response({"detail": msg}, status=status.HTTP_403_FORBIDDEN)

        serializer = InvoiceSerializer(invoice, context={'request': request})
        return Response(serializer.data)


class ProformaListCreate(HPListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
    serializer_class = ProformaSerializer
    queryset = Proforma.objects.all()


class ProformaRetrieveUpdate(generics.RetrieveUpdateAPIView):
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
    serializer_class = ProformaSerializer
    queryset = Proforma.objects.all()


class ProformaEntryCreate(DocEntryCreate):
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
    serializer_class = DocumentEntrySerializer
    queryset = DocumentEntry.objects.all()

    def post(self, request, *args, **kwargs):
        return super(ProformaEntryCreate, self).post(request, *args, **kwargs)

    def get_model(self):
        return Proforma

    def get_model_name(self):
        return "Proforma"


class ProformaEntryUpdateDestroy(DocEntryUpdateDestroy):
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
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


class ProformaStateHandler(APIView):
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
    serializer_class = ProformaSerializer

    def patch(self, request, *args, **kwargs):
        proforma_pk = kwargs.get('pk')
        try:
            proforma = Proforma.objects.get(pk=proforma_pk)
        except Proforma.DoesNotExist:
            return Response({"detail": "Proforma not found"},
                            status=status.HTTP_404_NOT_FOUND)

        state = request.DATA.get('state', None)
        if state == 'issued':
            if proforma.state != 'draft':
                msg = "A proforma can be issued only if it is in draft state."
                return Response({"detail": msg}, status=status.HTTP_403_FORBIDDEN)

            issue_date = request.DATA.get('issue_date', None)
            due_date = request.DATA.get('due_date', None)
            proforma.issue(issue_date, due_date)
            proforma.save()
        elif state == 'paid':
            if proforma.state != 'issued':
                msg = "A proforma can be paid only if it is in issued state."
                return Response({"detail": msg}, status=status.HTTP_403_FORBIDDEN)

            paid_date = request.DATA.get('paid_date', None)
            proforma.pay(paid_date)
            proforma.save()
        elif state == 'canceled':
            if proforma.state != 'issued':
                msg = "A proforma can be canceled only if it is in issued state."
                return Response({"detail": msg}, status=status.HTTP_403_FORBIDDEN)

            cancel_date = request.DATA.get('cancel_date', None)
            proforma.cancel(cancel_date)
            proforma.save()
        elif not state:
            msg = "You have to provide a value for the state field."
            return Response({"detail": msg}, status=status.HTTP_403_FORBIDDEN)
        else:
            msg = "Illegal state value."
            return Response({"detail": msg}, status=status.HTTP_403_FORBIDDEN)

        serializer = ProformaSerializer(proforma, context={'request': request})
        return Response(serializer.data)
