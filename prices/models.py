"""
PriceReport: what a product sold for at a market on a day. Same idea as the Hub's
market.PriceReport, so prices can later come straight from the Hub.
"""
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from accounts.choices import PRICE_FRESH_DAYS, PRODUCT_CHOICES, UNIT_CHOICES


class PriceReport(models.Model):
    crop = models.CharField("Product", max_length=20, choices=PRODUCT_CHOICES)
    unit = models.CharField(max_length=12, choices=UNIT_CHOICES)
    market = models.CharField(max_length=60, default="Mbare Musika")
    price_usd = models.DecimalField("Price (US$)", max_digits=10, decimal_places=2)
    price_zig = models.DecimalField("Price (ZiG)", max_digits=12, decimal_places=2, null=True, blank=True)
    date = models.DateField(default=timezone.localdate)
    note = models.CharField(max_length=120, blank=True, help_text="Where the price came from.")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "crop"]
        indexes = [models.Index(fields=["crop", "unit", "-date"])]
        constraints = [models.CheckConstraint(condition=models.Q(price_usd__gt=0), name="price_report_usd_positive")]

    def __str__(self):
        return f"{self.crop} per {self.get_unit_display()}: US${self.price_usd} at {self.market} on {self.date}"


def latest_price(crop, unit):
    """The newest report for this product and unit (old or not), or None."""
    return PriceReport.objects.filter(crop=crop, unit=unit).order_by("-date", "-id").first()


def compare(price_usd, report, today=None):
    """Where an asking price sits against a market report. Same rule as the page's meter:
    within 5% = "at", lower = "below", higher = "above"; older than PRICE_FRESH_DAYS = "stale"."""
    if report is None or price_usd is None:
        return None
    today = today or timezone.localdate()
    age = (today - report.date).days
    base = {"usd": float(report.price_usd), "market": report.market, "date": report.date.isoformat(), "age_days": age}
    if age > PRICE_FRESH_DAYS:
        return {**base, "stale": True}
    diff = (Decimal(str(price_usd)) - report.price_usd) / report.price_usd
    band = "below" if diff < Decimal("-0.05") else "above" if diff > Decimal("0.05") else "at"
    return {**base, "diff": float(round(diff, 4)), "band": band}


def latest_prices():
    """The newest report for every product and unit, for the page's live price checks."""
    seen, rows = set(), []
    for r in PriceReport.objects.order_by("crop", "unit", "-date", "-id"):
        if (r.crop, r.unit) not in seen:
            seen.add((r.crop, r.unit))
            rows.append({"crop": r.crop, "unit": r.unit, "usd": float(r.price_usd), "market": r.market, "date": r.date.isoformat()})
    return rows
