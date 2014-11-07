from django.conf.urls import patterns, url
from silver.api import views

urlpatterns = patterns(
    '',
    url(r'^subscriptions/$', views.SubscriptionList.as_view(),
        name='subscription-list'),
    url(r'^subscriptions/(?P<sub>[0-9]+)/$', views.SubscriptionDetail.as_view(),
        name='subscription-detail'),
    url(r'^subscriptions/(?P<sub>[0-9]+)/activate/$',
        views.SubscriptionDetailActivate.as_view(), name='sub-activate'),
    url(r'^subscriptions/(?P<sub>[0-9]+)/cancel/$',
        views.SubscriptionDetailCancel.as_view(), name='sub-cancel'),
    url(r'^subscriptions/(?P<sub>[0-9]+)/reactivate/$',
        views.SubscriptionDetailReactivate.as_view(), name='sub-reactivate'),
    url(
        r'^subscriptions/(?P<sub>[0-9]+)/(?P<mf>[0-9]+)/$',
        views.MeteredFeatureUnitsLogList.as_view(), name='mf-log-list'
    ),
    url(r'^customers/$', views.CustomerList.as_view(), name='customer-list'),
    url(r'^customers/(?P<pk>[0-9]+)/$', views.CustomerDetail.as_view(),
        name='customer-detail'),
    url(r'plans/?$', views.PlanList.as_view(), name='plan-list'),
    url(r'plans/(?P<pk>[0-9]+)/$', views.PlanDetail.as_view(),
        name='plan-detail'),
    url(r'plans/(?P<pk>[0-9]+)/metered_features/$',
        views.MeteredFeatures.as_view(), name='metered-features'),
    url(r'providers/$', views.ProviderList.as_view(), name='provider-list'),
)
