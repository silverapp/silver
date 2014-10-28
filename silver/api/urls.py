from django.conf.urls import patterns, url
from silver.api import views

urlpatterns = patterns(
    '',
    url(
        r'^subscriptions/(?P<sub>[^/]+)/(?P<mf>[^/]+)/?$',
        views.MeteredFeatureUnitsLogList.as_view()
    ),
    url(r'customers/?$', views.CustomerList.as_view()),
)
