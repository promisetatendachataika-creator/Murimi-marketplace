from django.urls import path

from . import api

app_name = "listings"

urlpatterns = [
    path("meta/", api.meta, name="meta"),
    path("stats/", api.stats, name="stats"),
    path("listings/", api.listings, name="list"),                                   # GET market / POST create
    path("listings/<int:listing_id>/", api.listing_detail, name="detail"),
    path("listings/<int:listing_id>/sold-out/", api.mark_sold_out, name="sold_out"),
    path("listings/<int:listing_id>/publish/", api.publish, name="publish"),
    path("listings/<int:listing_id>/report/", api.report_listing, name="report"),
    path("me/listings/", api.my_listings, name="mine"),
]
