"""
A farmer's track record as a seller: average stars from buyers and completed orders.
Worked out for a whole page of farmers in TWO queries (never one per card).
"""
from django.db.models import Avg, Count, F

from .models import Order, Rating


def seller_records(farmer_ids):
    """{farmer_id: (rating, completed_orders)} for the given farmers."""
    ids = set(farmer_ids)
    if not ids:
        return {}
    done = dict(Order.objects.filter(farmer_id__in=ids, status=Order.COMPLETED)
                .values_list("farmer_id").annotate(n=Count("id")).order_by())
    # Only stars that BUYERS gave the farmer count towards their seller rating.
    stars = dict(Rating.objects.filter(for_user_id__in=ids, for_user=F("order__farmer"))
                 .values_list("for_user_id").annotate(a=Avg("stars")).order_by())
    return {i: (round(float(stars.get(i) or 0), 1), done.get(i, 0)) for i in ids}


def seller_reviews(farmer, limit=5):
    """The latest written reviews buyers left for this farmer."""
    rows = (Rating.objects.filter(for_user=farmer, order__farmer=farmer).exclude(comment="")
            .select_related("by_user")[:limit])
    return [{"stars": r.stars, "comment": r.comment, "by": r.by_user.public_name(),
             "date": r.created_at.date().isoformat()} for r in rows]
