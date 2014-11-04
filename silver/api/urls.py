from django.conf.urls import patterns, url
from silver.api import views

urlpatterns = patterns(
    '',
    url(r'^subscriptions/?$', views.SubscriptionList.as_view()),
    url(r'^subscriptions/(?P<sub>[^/]+)/?$', views.SubscriptionDetail.as_view()),
    url(r'^subscriptions/(?P<sub>[^/]+)/activate/?$',
        views.SubscriptionDetailActivate.as_view()),
    url(
        r'^subscriptions/(?P<sub>[^/]+)/(?P<mf>[^/]+)/?$',
        views.MeteredFeatureUnitsLogList.as_view()
    ),
    url(r'^customers/?$', views.CustomerList.as_view()),
    url(r'^customers/(?P<pk>[^/]+)/?$', views.CustomerDetail.as_view(),
        name='customer-detail'),
    url(r'plans/(?P<pk>[^/]+)/?$', views.PlanDetail.as_view(),
        name='plan-detail'),
)
