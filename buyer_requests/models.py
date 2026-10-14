"""
BuyerRequest: "I need 300 crates of tomatoes every week in Harare."
Farmers answer with supply offers (orders.Order with proposed_by="farmer").
"filled" is never stored: it's worked out from the accepted supply orders, so it can't drift.
"""
from django.conf import settings
from django.db import models
from django.db.models import Q, Sum
from django.utils import timezone

from accounts.choices import PRODUCT_CHOICES, PROVINCE_CHOICES, UNIT_CHOICES

REPEAT_CHOICES = [("once", "Once"), ("weekly", "Every week"), ("fortnightly", "Every 2 weeks"), ("monthly", "Every month")]
REQUEST_DELIVERY = [("delivery", "Deliver to me"), ("pickup", "I'll collect"), ("either", "Either")]


class BuyerRequest(models.Model):
    OPEN, CLOSED = "open", "closed"

    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="buyer_requests")
    crop = models.CharField("Product", max_length=20, choices=PRODUCT_CHOICES)
    quantity = models.PositiveIntegerField()
    unit = models.CharField(max_length=12, choices=UNIT_CHOICES)
    province = models.CharField(max_length=30, choices=PROVINCE_CHOICES)
    district = models.CharField("Town or area", max_length=60, blank=True)
    needed_by = models.DateField()
    repeat = models.CharField("How often", max_length=12, choices=REPEAT_CHOICES, default="once")
    max_price_usd = models.DecimalField("Most they'll pay (US$)", max_digits=10, decimal_places=2, null=True, blank=True)
    delivery = models.CharField(max_length=10, choices=REQUEST_DELIVERY, default="delivery")
    note = models.CharField(max_length=300, blank=True)
    status = models.CharField(max_length=10, choices=[(OPEN, "Open"), (CLOSED, "Closed")], default=OPEN, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["needed_by"]
        indexes = [models.Index(fields=["status", "needed_by"])]
        constraints = [models.CheckConstraint(condition=Q(quantity__gt=0), name="request_quantity_positive")]

    def __str__(self):
        return f"#{self.pk} {self.quantity} {self.unit} {self.crop} for {self.buyer.name}"

    def filled(self):
        """How much farmers have agreed to supply (accepted or completed supply orders)."""
        return self.supply_orders.filter(status__in=["accepted", "completed"]).aggregate(n=Sum("quantity"))["n"] or 0

    def suppliers(self):
        return self.supply_orders.filter(status__in=["accepted", "completed"]).values("farmer").distinct().count()
