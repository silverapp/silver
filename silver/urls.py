"""URLs for the silver app."""

from django.conf import settings
from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.conf.urls.static import static

admin.autodiscover()

urlpatterns = patterns(
    '',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^api-auth/', include('rest_framework.urls',
                               namespace='rest_framework')),
    url(r'', include('silver.api.urls')),

) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
