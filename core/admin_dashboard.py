"""
The first page staff see after logging in to /admin/: what needs a person today.
Counts only (one query each); the lists are one click away.
"""
from datetime import timedelta

from django.contrib import admin
from django.urls import reverse
from django.utils import timezone

from accounts.choices import PRICE_FRESH_DAYS, PRODUCTS
from accounts.models import User
from buyer_requests.models import BuyerRequest
from listings.models import Listing, ListingReport
from orders.models import Order
from prices.models import latest_prices


def stale_price_products():
    """Products with no market price in the last PRICE_FRESH_DAYS days (the fair-price meter says "out of date" for these)."""
    cutoff = (timezone.localdate() - timedelta(days=PRICE_FRESH_DAYS)).isoformat()
    fresh = {r["crop"] for r in latest_prices() if r["date"] >= cutoff}
    return [c for c in PRODUCTS if c != "Other" and c not in fresh]


def dashboard_items():
    week = timezone.now() - timedelta(days=7)
    return [
        {"label": "Reports waiting for a look", "n": ListingReport.objects.filter(status="open").count(),
         "url": reverse("admin:listings_listingreport_changelist") + "?status__exact=open", "urgent": True},
        {"label": "Prices out of date (enter today's Mbare prices)", "n": len(stale_price_products()),
         "url": reverse("admin:prices_pricereport_add"), "urgent": True,
         "note": ", ".join(stale_price_products())},
        {"label": "Listings on the market", "n": Listing.objects.open().count(),
         "url": reverse("admin:listings_listing_changelist") + "?status__exact=active"},
        {"label": "Offers waiting for an answer", "n": Order.objects.filter(status="pending").count(),
         "url": reverse("admin:orders_order_changelist") + "?status__exact=pending"},
        {"label": "Open buyer requests", "n": BuyerRequest.objects.filter(status="open").count(),
         "url": reverse("admin:buyer_requests_buyerrequest_changelist") + "?status__exact=open"},
        {"label": "New accounts this week", "n": User.objects.filter(date_joined__gte=week, is_active=True).count(),
         "url": reverse("admin:accounts_user_changelist")},
        {"label": "Blocked or not yet confirmed accounts", "n": User.objects.filter(is_active=False).count(),
         "url": reverse("admin:accounts_user_changelist") + "?is_active__exact=0"},
    ]


def install():
    """Add the counts to the admin home page and give the back office our name."""
    admin.site.site_header = "Murimi Market staff"
    admin.site.site_title = "Murimi Market staff"
    admin.site.index_title = "What needs a person today"
    admin.site.index_template = "murimi/admin_index.html"
    original_index = admin.site.index

    def index(request, extra_context=None):
        ctx = dict(extra_context or {})
        if request.user.is_active and request.user.is_staff:
            ctx["murimi_items"] = dashboard_items()
        return original_index(request, ctx)

    admin.site.index = index
