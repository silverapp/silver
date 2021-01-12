from django.urls import re_path
from django.contrib import admin

from silver.urls import urlpatterns

admin.autodiscover()

# This urls.py file should be used when running silver as a standalone
# project (e.g. when running silver's tests)
urlpatterns = [
    re_path(r'^admin/', admin.site.urls),
] + urlpatterns
