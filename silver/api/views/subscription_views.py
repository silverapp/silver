import datetime
from decimal import Decimal

from annoying.functions import get_object_or_None
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, permissions, status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView

from silver.api.filters import MeteredFeaturesFilter, SubscriptionFilter
from silver.api.serializers.common import MeteredFeatureSerializer
from silver.api.serializers.subscriptions_serializers import SubscriptionSerializer, \
    SubscriptionDetailSerializer, MFUnitsLogSerializer
from silver.models import MeteredFeature, Subscription, MeteredFeatureUnitsLog
import logging

logger = logging.getLogger(__name__)


class MeteredFeatureList(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = MeteredFeatureSerializer
    queryset = MeteredFeature.objects.all()
    filter_backends = (DjangoFilterBackend,)
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
    filter_backends = (DjangoFilterBackend,)
    filter_class = SubscriptionFilter

    def get_queryset(self):
        customer_pk = self.kwargs.get('customer_pk', None)
        queryset = Subscription.objects.filter(customer__pk=customer_pk)
        return queryset.order_by('start_date')

    def post(self, request, *args, **kwargs):
        customer_pk = self.kwargs.get('customer_pk', None)
        url = reverse('customer-detail', kwargs={'customer_pk': customer_pk},
                      request=request)
        request.data.update({str('customer'): str(url)})

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

        if subscription.state not in [subscription.STATES.ACTIVE,
                                      subscription.STATES.CANCELED]:
            return Response({"detail": "Subscription is %s." % subscription.state},
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

        if not interval:
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
