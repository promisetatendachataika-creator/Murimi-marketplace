"""
Buyer requests JSON endpoints (shapes match what the pages already expect from api.js).

GET  /api/requests/                open requests whose date hasn't passed, soonest first
POST /api/requests/                a buyer posts what they need
POST /api/requests/<id>/supply/    a farmer offers to supply all or PART of it (creates an Order)
POST /api/requests/<id>/close/     only the buyer who posted it
GET  /api/me/requests/             my requests, with how many offers are waiting
"""
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_date

from accounts.choices import PRODUCTS, PROVINCES, READY_WINDOW_DAYS, units_for
from core.http import allow, json_error, read_json, throttle
from orders.api import MAX_MESSAGE, order_json
from orders.models import Order

from .models import REPEAT_CHOICES, REQUEST_DELIVERY, BuyerRequest

MAX_DAYS_AHEAD = 90
DONE = ["accepted", "completed"]


def with_fill(qs):
    """Add filled and suppliers to each request in the same query (no query per row)."""
    done = Q(supply_orders__status__in=DONE)
    return qs.annotate(filled_n=Sum("supply_orders__quantity", filter=done),
                       suppliers_n=Count("supply_orders__farmer", filter=done, distinct=True))


def request_json(r, me=None):
    if hasattr(r, "filled_n"):                     # worked out by with_fill()
        filled, suppliers = r.filled_n or 0, r.suppliers_n
    else:
        filled, suppliers = r.filled(), r.suppliers()
    return {
        "id": r.id, "buyer": {"name": r.buyer.public_name(), "kind": r.buyer.business_type or "Buyer"},
        "crop": r.crop, "quantity": r.quantity, "unit": r.unit,
        "filled": filled, "suppliers": suppliers, "still_needed": max(0, r.quantity - filled),
        "province": r.province, "district": r.district, "needed_by": r.needed_by.isoformat(),
        "repeat": r.repeat, "max_price_usd": float(r.max_price_usd) if r.max_price_usd is not None else None,
        "delivery": r.delivery, "note": r.note, "status": r.status,
        "created_at": timezone.localtime(r.created_at).strftime("%Y-%m-%dT%H:%M:%S"),
        "is_mine": bool(me and me.is_authenticated and r.buyer_id == me.id),
    }


def _read_request_form(data):
    errors = {}
    today = timezone.localdate()
    crop = data.get("crop", "")
    if crop not in PRODUCTS:
        errors["crop"] = "Choose a product from the list."
    unit = data.get("unit", "")
    if crop in PRODUCTS and unit not in units_for(crop):
        errors["unit"] = "That unit doesn't fit this product."
    try:
        qty = int(str(data.get("quantity", "")).strip())
    except ValueError:
        qty = 0
    if not 1 <= qty <= 1_000_000:
        errors["quantity"] = "Enter a whole number, 1 or more."
    province = data.get("province", "")
    if province not in PROVINCES:
        errors["province"] = "Choose the province where you need it."
    district = str(data.get("district") or "").strip()
    if len(district) > 60:
        errors["district"] = "Use 60 characters or fewer."
    needed = parse_date(str(data.get("needed_by") or ""))
    if not needed:
        errors["needed_by"] = "Choose the date you need it by."
    elif needed <= today:
        errors["needed_by"] = "Choose a date from tomorrow onwards."
    elif needed > today + timedelta(days=MAX_DAYS_AHEAD):
        errors["needed_by"] = "Requests can be up to 3 months ahead."
    repeat = data.get("repeat") or "once"
    if repeat not in dict(REPEAT_CHOICES):
        errors["repeat"] = "Choose how often you need it."
    raw_max = str(data.get("max_price") if data.get("max_price") is not None else "").strip()
    max_price = None
    if raw_max:
        try:
            max_price = Decimal(raw_max)
            if not Decimal("0.01") <= max_price <= Decimal("100000") or max_price.as_tuple().exponent < -2:
                raise InvalidOperation
        except InvalidOperation:
            errors["max_price"] = "Enter a price above 0 (cents at most), or leave it empty."
    delivery = data.get("delivery") or "delivery"
    if delivery not in dict(REQUEST_DELIVERY):
        errors["delivery"] = "Choose delivery or collection."
    note = str(data.get("note") or "").strip()
    if len(note) > MAX_MESSAGE:
        errors["note"] = "Keep the note under 300 characters."
    return dict(crop=crop, unit=unit, quantity=qty, province=province, district=district, needed_by=needed,
                repeat=repeat, max_price_usd=max_price, delivery=delivery, note=note), errors


@allow("GET", "POST")
def requests_view(request):
    if request.method == "GET":
        qs = with_fill(BuyerRequest.objects.filter(status=BuyerRequest.OPEN, needed_by__gte=timezone.localdate())
                       .select_related("buyer")).order_by("needed_by", "id")
        return JsonResponse({"results": [request_json(r, request.user) for r in qs[:100]]})

    if not request.user.is_authenticated:
        return json_error("Please log in to post a request.", status=401)
    if not request.user.can_buy:
        return json_error("Your account is for selling. Posting requests needs a buyer account; WhatsApp us to change it.",
                          status=403)
    over = throttle(request, "request", 10, 86400, "You've posted a lot of requests today. Please try again tomorrow.")
    if over:
        return over
    data, err = read_json(request)
    if err:
        return err
    cleaned, errors = _read_request_form(data)
    if errors:
        return json_error("Please check the form.", errors=errors)
    r = BuyerRequest.objects.create(buyer=request.user, **cleaned)
    return JsonResponse(request_json(r, request.user), status=201)


@allow("POST")
def supply(request, request_id):
    if not request.user.is_authenticated:
        return json_error("Please log in to offer.", status=401)
    me = request.user
    if not me.can_sell:
        return json_error("Supplying needs a farmer account; WhatsApp us to change it.", status=403)
    over = throttle(request, "supply", 30, 3600, "That's a lot of offers in an hour. Please wait a little before sending more.")
    if over:
        return over
    r = BuyerRequest.objects.select_related("buyer").filter(pk=request_id).first()
    if not r or r.status != BuyerRequest.OPEN or r.needed_by < timezone.localdate():
        return json_error("This request is closed.", status=404)
    if r.buyer_id == me.id:
        return json_error("This is your own request.")
    data, err = read_json(request)
    if err:
        return err

    errors, today = {}, timezone.localdate()
    still = r.quantity - r.filled()
    try:
        qty = int(str(data.get("quantity", "")).strip())
    except ValueError:
        qty = 0
    if qty < 1:
        errors["quantity"] = "Enter a whole number, 1 or more."
    elif qty > still:
        errors["quantity"] = f"They only need {still} more." if still > 0 else "This request is already fully supplied."
    try:
        price = Decimal(str(data.get("price", "")).strip())
        if not Decimal("0.01") <= price <= Decimal("100000") or price.as_tuple().exponent < -2:
            raise InvalidOperation
    except InvalidOperation:
        price = None
        errors["price"] = "Enter your price per unit."
    ready = parse_date(str(data.get("ready_on") or ""))
    if not ready or ready < today:
        errors["ready_on"] = "Choose when you can supply it."
    elif (ready - today).days > READY_WINDOW_DAYS:
        errors["ready_on"] = f"Offer to supply up to {READY_WINDOW_DAYS} days ahead."
    variety = str(data.get("variety") or "").strip()
    message = str(data.get("message") or "").strip()
    if len(variety) > 60:
        errors["variety"] = "Use 60 characters or fewer."
    if len(message) > MAX_MESSAGE:
        errors["message"] = "Keep the message under 300 characters."
    if errors:
        return json_error("Please check the form.", errors=errors)

    o = Order.objects.create(request=r, proposed_by=Order.BY_FARMER, farmer=me, buyer=r.buyer,
                             crop=r.crop, variety=variety or "As requested", unit=r.unit, price_usd=price,
                             quantity=qty, delivery="pickup" if r.delivery == "pickup" else "delivery",
                             message=message, ready_on=ready)
    return JsonResponse(order_json(o, me), status=201)


@allow("POST")
def close(request, request_id):
    if not request.user.is_authenticated:
        return json_error("Please log in.", status=401)
    r = BuyerRequest.objects.filter(pk=request_id).first()
    if not r or r.buyer_id != request.user.id:
        return json_error("Only the buyer who posted this can close it.", status=403)
    if r.status != BuyerRequest.CLOSED:
        r.status = BuyerRequest.CLOSED
        r.save(update_fields=["status"])
    return JsonResponse({"id": r.id, "status": r.status})


@allow("GET")
def my_requests(request):
    if not request.user.is_authenticated:
        return json_error("Please log in.", status=401)
    qs = with_fill(BuyerRequest.objects.filter(buyer=request.user).select_related("buyer")).order_by("-created_at")
    waiting = dict(Order.objects.filter(request__buyer=request.user, status=Order.PENDING)
                   .values_list("request_id").annotate(n=Count("id")).order_by())
    results = []
    for r in qs:
        d = request_json(r, request.user)
        d["offers_waiting"] = waiting.get(r.id, 0)
        results.append(d)
    return JsonResponse({"results": results})
