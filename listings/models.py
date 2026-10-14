"""
Listing       one lot of produce a farmer is selling.
ListingPhoto  up to 3 photos per listing (checked and cleaned on upload: see photos.py).

"Open" (visible on the market) means ALL of:
  status = active, quantity_left > 0, ready within READY_WINDOW_DAYS,
  and for "must sell today" listings: listed today and before 6 pm.
"""
from datetime import datetime, time, timedelta

from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from accounts.choices import (DELIVERY_CHOICES, PRODUCT_CHOICES, PROVINCE_CHOICES, READY_WINDOW_DAYS,
                              SELL_TODAY_ENDS_HOUR, UNIT_CHOICES)


class ListingQuerySet(models.QuerySet):
    def open(self, now=None):
        """Listings buyers can see right now (the market page)."""
        now = timezone.localtime(now)
        today = now.date()
        start_of_today = timezone.make_aware(datetime.combine(today, time.min))
        sell_today_ok = Q(sell_today=False) | Q(created_at__gte=start_of_today) if now.hour < SELL_TODAY_ENDS_HOUR else Q(sell_today=False)
        return self.filter(
            Q(status=Listing.ACTIVE), Q(quantity_left__gt=0),
            Q(available_from__lte=today + timedelta(days=READY_WINDOW_DAYS)),
        ).filter(sell_today_ok)


class Listing(models.Model):
    DRAFT, ACTIVE, SOLD_OUT, HIDDEN = "draft", "active", "sold_out", "hidden"
    STATUS_CHOICES = [(DRAFT, "Draft (only the farmer sees it)"), (ACTIVE, "On the market"),
                      (SOLD_OUT, "Sold out"), (HIDDEN, "Hidden by staff")]

    farmer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="listings")
    crop = models.CharField("Product", max_length=20, choices=PRODUCT_CHOICES)
    variety = models.CharField("Variety or grade", max_length=60, blank=True)
    quantity = models.PositiveIntegerField()
    quantity_left = models.PositiveIntegerField()
    unit = models.CharField(max_length=12, choices=UNIT_CHOICES)
    price_usd = models.DecimalField("Price per unit (US$)", max_digits=10, decimal_places=2)
    price_zig = models.DecimalField("Price per unit (ZiG)", max_digits=12, decimal_places=2, null=True, blank=True)
    province = models.CharField(max_length=30, choices=PROVINCE_CHOICES, blank=True)
    district = models.CharField("District or area", max_length=60, blank=True)
    available_from = models.DateField("Ready on", default=timezone.localdate)
    harvested_on = models.DateField(null=True, blank=True)
    delivery = models.CharField(max_length=10, choices=DELIVERY_CHOICES, default="both")
    sell_today = models.BooleanField("Must sell today", default=False)
    description = models.TextField(max_length=500, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=ACTIVE, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ListingQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "crop", "province"]),       # the market filters
            models.Index(fields=["status", "-created_at"]),            # "newest first"
            models.Index(fields=["farmer", "-created_at"]),            # My listings
        ]
        constraints = [
            models.CheckConstraint(condition=Q(quantity_left__lte=F("quantity")), name="listing_left_not_more_than_quantity"),
            models.CheckConstraint(condition=Q(price_usd__gt=0) | Q(status="draft"), name="listing_price_positive_unless_draft"),
        ]

    def __str__(self):
        return f"#{self.pk} {self.crop} {self.variety} ({self.quantity_left}/{self.quantity} {self.unit})"

    @property
    def ready_in_days(self):
        return max(0, (self.available_from - timezone.localdate()).days)

    def ends_at(self):
        """For "must sell today": the moment it leaves the market."""
        if not self.sell_today:
            return None
        return timezone.localtime(self.created_at).replace(hour=SELL_TODAY_ENDS_HOUR, minute=0, second=0, microsecond=0)


def photo_path(instance, filename):
    when = timezone.localdate()
    return f"listings/{when:%Y/%m}/{filename}"


class ListingPhoto(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to=photo_path)
    position = models.PositiveSmallIntegerField(default=0)    # 0 = the cover photo
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self):
        return f"Photo {self.position + 1} of listing #{self.listing_id}"
