from rest_framework import generics, permissions
from rest_framework.response import Response
from silver.models import MeteredFeatureUnitsLog, Subscription, MeteredFeature, \
    Customer
from silver.api.serializers import MeteredFeatureUnitsLogSerializer, \
    CustomerSerializer
import datetime


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
        consumed_units = request.DATA.get('consumed_units', None)
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
                print subscription.current_start_date
                print subscription.current_end_date
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
                                MeteredFeatureUnitsLog.objects.create(
                                    metered_feature=metered_feature,
                                    subscription=subscription,
                                    start_date=subscription.current_start_date,
                                    end_date=subscription.current_end_date,
                                    consumed_units=consumed_units
                                )
                            return Response({"success": True}, status=200)
                    except TypeError:
                        return Response({"success": False}, status=400)
                else:
                    return Response({"success": False}, status=400)
            else:
                return Response({"detail": "Not found"}, status=404)
        return Response({"success": False}, status=400)


class CustomerList(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
    serializer_class = CustomerSerializer
    model = Customer
