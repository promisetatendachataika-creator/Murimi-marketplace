"""
The front door map (ROOT_URLCONF in settings.py points here).

Every request's path, e.g. /admin/ or /api/health/, is checked against this
list from top to bottom. The first match decides which code answers.
No match -> Django answers 404 "Not Found".
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),   # staff back office
    path("", include("web.urls")),     # the marketplace page at /
    # Later: path("api/", include("listings.urls")), ...
]
