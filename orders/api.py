"""
Offers and orders JSON endpoints (shapes match what the pages already expect from api.js).

POST /api/listings/<id>/offers/      a buyer sends an offer on a listing
GET  /api/me/offers/                 orders where I'm the farmer (offers on my listings + my supply offers)
GET  /api/me/orders/                 orders where I'm the buyer (what I asked to buy + supply offers to my requests)
POST /api/orders/<id>/<action>/      accept | decline | cancel | complete
POST /api/orders/<id>/rating/        { stars, comment }  once per side, after completed

Never trust the browser: every rule is checked here again.
The other side's phone number is only sent once the order is accepted (the "contact reveal").
"""
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.utils import timezone

from core.http import allow, json_error, read_json, throttle
from listings.models import Listing

from .models import TRANSITIONS, Order, Rating

MAX_MESSAGE = 300


def _day(dt):
    return timezone.localtime(dt).strftime("%Y-%m-%dT%H:%M:%S") if dt else None


def order_json(o, me):
    """One order as `me` sees it."""
    i_am_farmer = o.farmer_id == me.id
    other = o.buyer if i_am_farmer else o.farmer
    revealed = o.status in (Order.ACCEPTED, Order.COMPLETED)
    ratings = {r.by_user_id: r for r in o.ratings.all()}
    mine, theirs = ratings.get(me.id), ratings.get(other.id)
    can = [a for a in TRANSITIONS if o.may(a, me)]
    if o.status == Order.COMPLETED and not mine:
        can.append("rate")
    rating = lambda r: {"stars": r.stars, "comment": r.comment} if r else None  # noqa: E731
    return {
        "id": o.id, "listing_id": o.listing_id, "request_id": o.request_id,
        "crop": o.crop, "variety": o.variety, "unit": o.unit, "price_usd": float(o.price_usd),
        "quantity": o.quantity, "total_usd": float(o.total_usd), "delivery": o.delivery, "message": o.message,
        "status": o.status, "created_at": _day(o.created_at), "accepted_at": _day(o.accepted_at),
        "completed_at": _day(o.completed_at), "ready_on": o.ready_on.isoformat() if o.ready_on else None,
        "my_side": "farmer" if i_am_farmer else "buyer", "proposed_by": o.proposed_by,
        "i_sent": o.sender().id == me.id,
        "other_party": {"name": other.public_name() if not revealed else other.name,
                        "phone": other.phone if revealed else None},
        "my_rating": rating(mine), "their_rating": rating(theirs), "can": can,
    }


def _orders_for(me, **side):
    return (Order.objects.filter(**side).select_related("farmer", "buyer")
            .prefetch_related("ratings").order_by("-created_at"))


def _need_login(request):
    if not request.user.is_authenticated:
        return json_error("Please log in.", status=401)
    return None


# ---------------------------------------------------------------- sending an offer
@allow("POST")
def send_offer(request, listing_id):
    if not request.user.is_authenticated:
        return json_error("Please log in to send an offer.", status=401)
    me = request.user
    over = throttle(request, "offer", 30, 3600, "That's a lot of offers in an hour. Please wait a little before sending more.")
    if over:
        return over
    if not me.can_buy:
        return json_error("Your account is for selling. Buying needs a buyer account; WhatsApp us to change it.", status=403)
    data, err = read_json(request)
    if err:
        return err
    l = Listing.objects.open().select_related("farmer").filter(pk=listing_id).first()
    if not l:
        return json_error("This listing is no longer available.", status=404)
    if l.farmer_id == me.id:
        return json_error("This is your own listing.")

    errors = {}
    try:
        qty = int(str(data.get("quantity", "")).strip())
    except ValueError:
        qty = 0
    if not (1 <= qty <= l.quantity_left):
        errors["quantity"] = f"Choose between 1 and {l.quantity_left}."
    delivery = data.get("delivery")
    if delivery not in ("pickup", "delivery"):
        errors["delivery"] = "Choose collection or delivery."
    elif l.delivery != "both" and delivery != l.delivery:
        errors["delivery"] = "This farmer only offers collection." if l.delivery == "pickup" else "This farmer only delivers."
    message = str(data.get("message") or "").strip()
    if len(message) > MAX_MESSAGE:
        errors["message"] = "Keep the message under 300 characters."
    if errors:
        return json_error("Please check the form.", errors=errors)
    if Order.objects.filter(listing=l, buyer=me, status=Order.PENDING).exists():
        return json_error("You already have an offer waiting on this listing. Cancel it in My account to send a new one.", status=409)

    o = Order.objects.create(listing=l, proposed_by=Order.BY_BUYER, farmer=l.farmer, buyer=me,
                             crop=l.crop, variety=l.variety, unit=l.unit, price_usd=l.price_usd,
                             quantity=qty, delivery=delivery, message=message,
                             ready_on=l.available_from if l.ready_in_days > 0 else None)
    return JsonResponse(order_json(o, me), status=201)


# ---------------------------------------------------------------- my lists
@allow("GET")
def my_offers(request):
    """SQL: SELECT ... FROM order WHERE farmer_id = me ORDER BY created_at DESC"""
    if (err := _need_login(request)):
        return err
    return JsonResponse({"results": [order_json(o, request.user) for o in _orders_for(request.user, farmer=request.user)]})


@allow("GET")
def my_orders(request):
    if (err := _need_login(request)):
        return err
    return JsonResponse({"results": [order_json(o, request.user) for o in _orders_for(request.user, buyer=request.user)]})


# ---------------------------------------------------------------- answering
WHO_MESSAGES = {"receiver": "Only the person who received this offer can answer it.",
                "sender": "Only the person who sent this offer can cancel it."}


@allow("POST")
def order_action(request, order_id, action):
    if (err := _need_login(request)):
        return err
    me = request.user
    over = throttle(request, "order-action", 200, 3600)
    if over:
        return over
    t = TRANSITIONS.get(action)
    if not t:
        return json_error("Unknown action.", status=404)

    with transaction.atomic():
        # Lock this order's row until we finish, so two clicks can't both go through.
        o = Order.objects.select_for_update().filter(pk=order_id).first()
        if not o or me.id not in (o.farmer_id, o.buyer_id):
            return json_error("Order not found.", status=404)
        if o.status not in t["from"]:
            return json_error(f"This order is already {o.status}.", status=409)
        if not o.may(action, me):
            return json_error(WHO_MESSAGES[t["who"]], status=403)

        if action == "accept" and o.listing_id:
            # SELECT ... FOR UPDATE: two accepts at once can never sell the same last crate twice.
            l = Listing.objects.select_for_update().get(pk=o.listing_id)
            if l.status != Listing.ACTIVE or l.quantity_left < 1:
                return json_error("This listing is sold out.", status=409)
            if l.quantity_left < o.quantity:
                return json_error(f"Only {l.quantity_left} left, but this offer asks for {o.quantity}. "
                                  "Decline it, or ask the buyer to send a smaller offer.", status=409)
            l.quantity_left -= o.quantity
            l.save(update_fields=["quantity_left", "updated_at"])
        elif action == "accept":
            from buyer_requests.models import BuyerRequest
            r = BuyerRequest.objects.select_for_update().get(pk=o.request_id)
            if r.status != BuyerRequest.OPEN:
                return json_error("This request is closed.", status=409)
            still = r.quantity - r.filled()
            if o.quantity > still:
                return json_error(f"Only {still} still needed, but this offer is for {o.quantity}. "
                                  "Decline it, or ask the farmer for a smaller amount." if still > 0
                                  else "This request is already fully supplied.", status=409)

        o.status = t["to"]
        now = timezone.now()
        if action == "accept":
            o.accepted_at = now
        if action == "complete":
            o.completed_at = now
        o.save()
    o = _orders_for(me, pk=o.pk).get()
    return JsonResponse(order_json(o, me))


@allow("POST")
def rate_order(request, order_id):
    if (err := _need_login(request)):
        return err
    me = request.user
    over = throttle(request, "rating", 60, 3600)
    if over:
        return over
    o = Order.objects.select_related("farmer", "buyer").filter(pk=order_id).first()
    if not o or me.id not in (o.farmer_id, o.buyer_id):
        return json_error("Order not found.", status=404)
    if o.status != Order.COMPLETED:
        return json_error("You can rate once the order is completed.", status=409)
    data, err = read_json(request)
    if err:
        return err
    try:
        stars = int(data.get("stars"))
    except (TypeError, ValueError):
        stars = 0
    if not 1 <= stars <= 5:
        return json_error("Please check the form.", errors={"stars": "Choose 1 to 5 stars."})
    comment = str(data.get("comment") or "").strip()
    if len(comment) > MAX_MESSAGE:
        return json_error("Please check the form.", errors={"comment": "Keep it under 300 characters."})
    other = o.buyer if o.farmer_id == me.id else o.farmer
    try:
        with transaction.atomic():      # the database's "one rating per side" rule is the final guard
            Rating.objects.create(order=o, by_user=me, for_user=other, stars=stars, comment=comment)
    except IntegrityError:
        return json_error("You've already rated this order.", status=409)
    o = _orders_for(me, pk=o.pk).get()
    return JsonResponse(order_json(o, me), status=201)
