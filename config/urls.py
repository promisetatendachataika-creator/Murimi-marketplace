"""
The front door map (ROOT_URLCONF in settings.py points here).

Every request's path, e.g. /admin/ or /api/health/, is checked against this
list from top to bottom. The first match decides which code answers.
No match -> Django answers 404 "Not Found".
"""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path(settings.ADMIN_PATH, admin.site.urls),   # staff back office (/admin/ unless DJANGO_ADMIN_PATH says otherwise)
    path("api/", include("core.urls")),  # JSON for the pages' JavaScript (api.js)
    path("", include("web.urls")),     # the marketplace pages: /, /login/, /listing/101/ ...
]

# Farmers' photos. WhiteNoise handles our own CSS and JavaScript, but not files people
# upload after the site is running, so Django serves those itself. That is fine at this size
# (a few thousand photos, read straight off the disk). If the market ever grows enough that
# photos slow the site down, move them to a storage service and delete these three lines.
urlpatterns += [
    re_path(r"^%s(?P<path>.*)$" % settings.MEDIA_URL.lstrip("/"), serve, {"document_root": settings.MEDIA_ROOT}),
]
