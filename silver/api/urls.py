from django.conf.urls import patterns, url
from silver.api import views

urlpatterns = patterns(
    '',
    url(
        r'^subscriptions/(?P<sub>[^/]+)/(?P<mf>[^/]+)/?',
        views.MeteredFeatureLogList.as_view()
    ),
)
