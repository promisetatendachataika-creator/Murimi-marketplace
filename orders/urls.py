from django.urls import path

from . import api

urlpatterns = [
    path("listings/<int:listing_id>/offers/", api.send_offer, name="send-offer"),
    path("me/offers/", api.my_offers, name="my-offers"),
    path("me/orders/", api.my_orders, name="my-orders"),
    path("orders/<int:order_id>/rating/", api.rate_order, name="rate-order"),
    path("orders/<int:order_id>/<slug:action>/", api.order_action, name="order-action"),
]
