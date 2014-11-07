from rest_framework import generics, permissions, status, filters
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from silver.models import (MeteredFeatureUnitsLog, Subscription, MeteredFeature,
                           Customer, Plan)
from silver.api.serializers import (MeteredFeatureUnitsLogSerializer,
                                    CustomerSerializer, SubscriptionSerializer,
                                    SubscriptionDetailSerializer,
                                    PlanSerializer, MeteredFeatureSerializer)
import datetime


class PlanList(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
    serializer_class = PlanSerializer
    queryset = Plan.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filter_fields = ('enabled', 'private')


class PlanDetail(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
    serializer_class = PlanSerializer
    model = Plan
    lookup_field = 'pk'

    def patch(self, request, *args, **kwargs):
        plan = get_object_or_404(Plan.objects, pk=self.kwargs.get('pk', None))
        name = request.DATA.get('name', None)
        generate_after = request.DATA.get('generate_after', None)
        due_days = request.DATA.get('due_days', None)
        plan.name = name or plan.name
        plan.generate_after = generate_after or plan.generate_after
        plan.due_days = due_days or plan.due_days
        plan.save()
        return Response(PlanSerializer(plan).data, status=status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        plan = get_object_or_404(Plan.objects, pk=self.kwargs.get('pk', None))
        plan.enabled = False
        plan.save()
        return Response({"enabled": plan.enabled}, status=status.HTTP_200_OK)


class MeteredFeatures(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
    serializer_class = MeteredFeatureSerializer
    model = MeteredFeature
    lookup_field = 'plan'
    lookup_url_kwarg = 'pk'


class SubscriptionList(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
    model = Subscription
    serializer_class = SubscriptionSerializer


class SubscriptionDetail(generics.RetrieveAPIView):
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
    model = Subscription
    serializer_class = SubscriptionDetailSerializer
    lookup_url_kwarg = 'sub'
    lookup_field = 'pk'


class SubscriptionDetailActivate(APIView):
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)

    def post(self, request, *args, **kwargs):
        sub = get_object_or_404(Subscription.objects,
                                pk=self.kwargs.get('pk', None))
        if sub.state != 'inactive':
            message = 'Cannot activate subscription from %s state.' % sub.state
            return Response({"error": message},
                            status=status.HTTP_400_BAD_REQUEST)
        else:
            if request.POST['_content']:
                start_date = request.DATA.get('start_date', None)
                trial_end = request.DATA.get('trial_end_date', None)
                sub.activate(start_date=start_date, trial_end_date=trial_end)
                sub.save()
            else:
                sub.activate()
                sub.save()
            return Response({"state: %s" % sub.state},
                            status=status.HTTP_200_OK)


class SubscriptionDetailCancel(APIView):
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)

    def post(self, request, *args, **kwargs):
        sub = get_object_or_404(Subscription.objects,
                                pk=self.kwargs.get('sub', None))
        when = request.DATA.get('when', None)
        if sub.state != 'active':
            message = 'Cannot cancel subscription from %s state.' % sub.state
            return Response({"error": message},
                            status=status.HTTP_400_BAD_REQUEST)
        else:
            if when == 'now':
                sub.cancel()
                sub.end()
                sub.save()
                return Response({"state: %s" % sub.state},
                                status=status.HTTP_200_OK)
            elif when == 'end_of_billing_cycle':
                sub.cancel()
                sub.save()
                return Response({"state: %s" % sub.state},
                                status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_400_BAD_REQUEST)


class SubscriptionDetailReactivate(APIView):
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)

    def post(self, request, *args, **kwargs):
        sub = get_object_or_404(Subscription.objects,
                                pk=self.kwargs.get('sub', None))
        if sub.state != 'canceled':
            message = 'Cannot reactivate subscription from %s state.' % sub.state
            return Response({"error": message},
                            status=status.HTTP_400_BAD_REQUEST)
        else:
            sub.activate()
            sub.save()
            return Response({"state: %s" % sub.state},
                            status=status.HTTP_200_OK)


class MeteredFeatureUnitsLogList(generics.ListAPIView):
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
    serializer_class = MeteredFeatureUnitsLogSerializer

    def get_queryset(self):
        return MeteredFeatureUnitsLog.objects.filter(
            metered_feature=self.kwargs['mf'],
            subscription=self.kwargs['sub'],
        )

    def patch(self, request, *args, **kwargs):
        metered_feature_pk = self.kwargs['mf']
        subscription_pk = self.kwargs['sub']
        date = request.DATA.get('date', None)
        consumed_units = request.DATA.get('count', None)
        update_type = request.DATA.get('update_type', None)

        if subscription_pk and metered_feature_pk:
            try:
                subscription = Subscription.objects.get(pk=subscription_pk)
            except Subscription.DoesNotExist:
                subscription = None
            try:
                metered_feature = MeteredFeature.objects.get(pk=metered_feature_pk)
            except MeteredFeature.DoesNotExist:
                metered_feature = None
            if subscription and metered_feature:
                if subscription.state != 'active':
                    return Response({"detail": "Subscription is not active"},
                                    status=status.HTTP_403_FORBIDDEN)
                if date and consumed_units is not None and update_type:
                    try:
                        date = datetime.datetime.strptime(date,
                                                          '%Y-%m-%d').date()
                        if subscription.current_start_date <= date <= \
                           subscription.current_end_date:
                            try:
                                log = MeteredFeatureUnitsLog.objects.get(
                                    start_date__lte=date,
                                    end_date__gte=date,
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


class CustomerList(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
    serializer_class = CustomerSerializer
    model = Customer


class CustomerDetail(generics.RetrieveUpdateAPIView):
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
    serializer_class = CustomerSerializer
    model = Customer
    lookup_field = 'pk'
