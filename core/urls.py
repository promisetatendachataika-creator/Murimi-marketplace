"""
Addresses under /api/ (config/urls.py sends everything starting with "api/" here).

Order matters: Django tries each line from the top. The catch-all must stay LAST,
or it would swallow every address below it.
"""
from django.urls import include, path

from . import api

app_name = "core"

urlpatterns = [
    path("health/", api.health, name="health"),          # GET /api/health/
    path("auth/", include("accounts.urls")),             # /api/auth/login/, /api/auth/me/ ...
    path("", include("listings.urls")),                  # /api/meta/, /api/stats/, /api/listings/ ...
    # Next: offers, requests ...
    path("<path:rest>", api.not_found),                  # anything else under /api/  -> JSON 404
]
