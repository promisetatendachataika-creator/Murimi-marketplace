"""
Addresses under /api/ (config/urls.py sends everything starting with "api/" here).

Order matters: Django tries each line from the top. The catch-all must stay LAST,
or it would swallow every address below it.
"""
from django.urls import path

from . import api

app_name = "core"

urlpatterns = [
    path("health/", api.health, name="health"),          # GET /api/health/
    # Later lessons add: accounts, listings, offers, requests ...
    path("<path:rest>", api.not_found),                  # anything else under /api/  -> JSON 404
]
