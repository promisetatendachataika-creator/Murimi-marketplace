from django.urls import path

from . import api

urlpatterns = [
    path("requests/", api.requests_view, name="requests"),
    path("requests/<int:request_id>/supply/", api.supply, name="request-supply"),
    path("requests/<int:request_id>/close/", api.close, name="request-close"),
    path("me/requests/", api.my_requests, name="my-requests"),
]
