"""
Order    one offer, from first message to finished deal. Two kinds share ONE table:
           - an offer on a listing:      the buyer sends it, the farmer answers  (proposed_by = "buyer")
           - a supply offer on a request: the farmer sends it, the buyer answers (proposed_by = "farmer")
         status: pending -> accepted -> completed, or declined / cancelled.
         Crop, unit and price are COPIED from the listing when the offer is made, so a later
         price change on the listing never changes an agreed deal.
Rating   after "completed", each side rates the other once (1 to 5 stars).
"""
from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from accounts.choices import PRODUCT_CHOICES, UNIT_CHOICES

# THE STATUS RULES (the page's old demo had the same table).
#   receiver = whoever received the offer, sender = whoever sent it.
TRANSITIONS = {
    "accept":   {"from": ["pending"],  "who": "receiver", "to": "accepted"},
    "decline":  {"from": ["pending"],  "who": "receiver", "to": "declined"},
    "cancel":   {"from": ["pending"],  "who": "sender",   "to": "cancelled"},
    "complete": {"from": ["accepted"], "who": "either",   "to": "completed"},
}


class Order(models.Model):
    PENDING, ACCEPTED, DECLINED, CANCELLED, COMPLETED = "pending", "accepted", "declined", "cancelled", "completed"
    STATUS_CHOICES = [(PENDING, "Waiting for an answer"), (ACCEPTED, "Accepted"), (DECLINED, "Declined"),
                      (CANCELLED, "Cancelled"), (COMPLETED, "Completed")]
    BY_BUYER, BY_FARMER = "buyer", "farmer"

    listing = models.ForeignKey("listings.Listing", null=True, blank=True, on_delete=models.PROTECT, related_name="orders")
    request = models.ForeignKey("buyer_requests.BuyerRequest", null=True, blank=True, on_delete=models.PROTECT,
                                related_name="supply_orders")
    proposed_by = models.CharField(max_length=6, choices=[(BY_BUYER, "Buyer"), (BY_FARMER, "Farmer")], default=BY_BUYER)
    farmer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders_as_farmer")
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders_as_buyer")
    crop = models.CharField("Product", max_length=20, choices=PRODUCT_CHOICES)
    other_product = models.CharField(max_length=40, blank=True)   # copied from the listing, for "Other"
    variety = models.CharField(max_length=60, blank=True)
    unit = models.CharField(max_length=12, choices=UNIT_CHOICES)
    price_usd = models.DecimalField("Price per unit (US$)", max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    delivery = models.CharField(max_length=10, choices=[("pickup", "Buyer collects"), ("delivery", "Farmer delivers")])
    message = models.CharField(max_length=300, blank=True)
    ready_on = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)
    accepted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["farmer", "status"]), models.Index(fields=["buyer", "status"])]
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gt=0), name="order_quantity_positive"),
            models.CheckConstraint(condition=Q(price_usd__gt=0), name="order_price_positive"),
            models.CheckConstraint(condition=~Q(farmer=F("buyer")), name="order_not_with_yourself"),
            # Exactly one of: an offer on a listing, or a supply offer on a request.
            models.CheckConstraint(condition=(Q(listing__isnull=False, request__isnull=True) |
                                              Q(listing__isnull=True, request__isnull=False)),
                                   name="order_listing_or_request"),
        ]

    def __str__(self):
        return f"#{self.pk} {self.quantity} {self.unit} {self.crop}: {self.buyer.name} / {self.farmer.name} ({self.status})"

    @property
    def product_name(self):
        return self.other_product or self.crop

    @property
    def total_usd(self):
        return self.quantity * self.price_usd

    def sender(self):
        return self.buyer if self.proposed_by == self.BY_BUYER else self.farmer

    def may(self, action, user):
        """Can `user` do `action` (accept, decline, cancel, complete) on this order right now?"""
        t = TRANSITIONS.get(action)
        if not t or self.status not in t["from"] or user.id not in (self.farmer_id, self.buyer_id):
            return False
        if t["who"] == "either":
            return True
        i_sent = self.sender().id == user.id
        return i_sent if t["who"] == "sender" else not i_sent


class Rating(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="ratings")
    by_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ratings_given")
    for_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ratings_received")
    stars = models.PositiveSmallIntegerField()
    comment = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["order", "by_user"], name="one_rating_per_side"),
            models.CheckConstraint(condition=Q(stars__gte=1, stars__lte=5), name="stars_1_to_5"),
        ]

    def __str__(self):
        return f"{self.stars} stars for {self.for_user.name} (order #{self.order_id})"
