"""
Listings JSON endpoints (the shapes match what the pages already expect from api.js).

GET  /api/meta/                    lists for menus + latest market prices
GET  /api/stats/                   open listings, verified farmers, listings per province (the map)
GET  /api/listings/                the market: filters, sort, pages of 12
POST /api/listings/                create (form fields + up to 3 photo files)
GET  /api/listings/<id>/           one listing in full
POST /api/listings/<id>/sold-out/  owner only
POST /api/listings/<id>/publish/   owner only: draft -> on the market
POST /api/listings/<id>/report/    anyone logged in: flag a listing for staff
GET  /api/me/listings/             my listings (drafts and sold out too)
"""
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.db import IntegrityError, transaction
from django.db.models import Case, Count, DecimalField, ExpressionWrapper, F, OuterRef, Q, Subquery, Value, When
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date

from accounts.choices import (CROPS, DELIVERY_CHOICES, POULTRY, PRICE_FRESH_DAYS, PRODUCT_UNITS, PRODUCTS,
                              PROVINCES, READY_WINDOW_DAYS, UNIT_CHOICES, CROP_UNITS, units_for)
from core.http import allow, json_error, rate_limited, read_json, throttle
from orders.records import seller_records, seller_reviews
from prices.models import PriceReport, compare, latest_price, latest_prices

from .models import Listing, ListingPhoto, ListingReport
from .photos import PhotoError, clean_photo

PAGE_SIZE = 12
REPORTS_PER_DAY = 10
MAX_PHOTOS = 3
REPEATS = [{"value": "once", "label": "Once"}, {"value": "weekly", "label": "Every week"},
           {"value": "fortnightly", "label": "Every 2 weeks"}, {"value": "monthly", "label": "Every month"}]


# ---------------------------------------------------------------- shaping JSON
def farmer_card(user, records=None):
    """What buyers see about a farmer on a card. Never the phone number.
    records = seller_records() for a whole page (two queries), or None to look this one farmer up."""
    if records is None:
        records = seller_records([user.id])
    rating, completed = records.get(user.id, (0, 0))
    return {"id": user.id, "name": user.public_name(), "verified": user.is_verified_farmer,
            "rating": rating, "completed_orders": completed}       # 0 completed shows "New seller"


def photo_urls(listing, request):
    return [request.build_absolute_uri(p.image.url) for p in listing.photos.all()]


_LOOK_UP = object()   # "work the market price out yourself" (a missing price is None, which is a real answer)


def listing_json(l, request, market=_LOOK_UP, records=None):
    photos = photo_urls(l, request)
    return {
        "id": l.id, "status": l.status, "crop": l.crop, "variety": l.variety,
        "quantity": l.quantity, "quantity_left": l.quantity_left, "unit": l.unit,
        "price_usd": float(l.price_usd), "price_zig": float(l.price_zig) if l.price_zig is not None else None,
        "province": l.province, "district": l.district,
        "available_from": l.available_from.isoformat(), "ready_in_days": l.ready_in_days,
        "harvested_on": l.harvested_on.isoformat() if l.harvested_on else None,
        "delivery": l.delivery, "sell_today": l.sell_today,
        "ends_at": l.ends_at().strftime("%Y-%m-%dT%H:%M") if l.sell_today else None,
        "created_at": timezone.localtime(l.created_at).strftime("%Y-%m-%dT%H:%M:%S"),
        "photo_url": photos[0] if photos else None,
        "market": compare(l.price_usd, latest_price(l.crop, l.unit)) if market is _LOOK_UP else market,
        "farmer": farmer_card(l.farmer, records),
    }


def market_cache():
    """Latest report per (crop, unit) in one query, for a whole page of cards."""
    latest = {}
    for r in PriceReport.objects.order_by("crop", "unit", "-date", "-id"):
        latest.setdefault((r.crop, r.unit), r)
    return latest


# ---------------------------------------------------------------- meta + stats
@allow("GET")
def meta(request):
    return JsonResponse({
        "crops": CROPS, "poultry": POULTRY, "products": PRODUCTS, "provinces": PROVINCES,
        "units": [{"value": v, "label": l} for v, l in UNIT_CHOICES],
        "product_units": {**PRODUCT_UNITS, "_crops": CROP_UNITS},
        "ready_window_days": READY_WINDOW_DAYS, "price_fresh_days": PRICE_FRESH_DAYS,
        "repeats": REPEATS, "prices": latest_prices(),
    })


@allow("GET")
def stats(request):
    """SQL: SELECT province, COUNT(*) FROM listing WHERE <open> GROUP BY province"""
    open_ = Listing.objects.open()
    by_province = {row["province"]: row["n"] for row in open_.values("province").annotate(n=Count("id")).order_by()}
    return JsonResponse({
        "listings": open_.count(),
        "verified_farmers": open_.filter(farmer__is_verified_farmer=True).values("farmer").distinct().count(),
        "by_province": by_province,
    })


# ---------------------------------------------------------------- the market
def _market_queryset(params):
    qs = Listing.objects.open().select_related("farmer").prefetch_related("photos")
    today = timezone.localdate()
    if params.get("crop") in PRODUCTS:
        qs = qs.filter(crop=params["crop"])                               # WHERE crop = ?
    if params.get("province") in PROVINCES:
        qs = qs.filter(province=params["province"])                       # AND province = ?
    try:
        if params.get("max_price"):
            qs = qs.filter(price_usd__lte=Decimal(params["max_price"]))   # AND price_usd <= ?
    except InvalidOperation:
        pass
    if params.get("ready") == "now":
        qs = qs.filter(available_from__lte=today)
    elif params.get("ready") == "soon":
        qs = qs.filter(available_from__gt=today)
    if params.get("sell_today") in ("1", "true"):
        qs = qs.filter(sell_today=True)

    sort = params.get("sort", "newest")
    if sort == "price_asc":
        return qs.order_by("price_usd", "-created_at")
    if sort == "price_desc":
        return qs.order_by("-price_usd", "-created_at")
    if sort == "fair":
        # Best value vs market: asking price / latest FRESH market price for the same product and unit,
        # worked out inside the database with a subquery. Listings with no fresh price go last.
        fresh = PriceReport.objects.filter(crop=OuterRef("crop"), unit=OuterRef("unit"),
                                           date__gte=today - timedelta(days=PRICE_FRESH_DAYS)).order_by("-date", "-id")
        qs = qs.annotate(market_usd=Subquery(fresh.values("price_usd")[:1]))
        qs = qs.annotate(ratio=Case(
            When(market_usd__isnull=True, then=Value(None)),
            default=ExpressionWrapper(F("price_usd") / F("market_usd"), output_field=DecimalField(max_digits=12, decimal_places=4)),
        ))
        return qs.order_by(F("ratio").asc(nulls_last=True), "-created_at")
    return qs.order_by("-created_at")


def _read_listing_form(data, files, draft):
    """Check a Sell form. Returns (cleaned dict, errors dict)."""
    errors, out = {}, {}
    today = timezone.localdate()

    crop = data.get("crop", "")
    if crop not in PRODUCTS:
        errors["crop"] = "Choose a product from the list."
    unit = data.get("unit", "")
    if unit and unit not in dict(UNIT_CHOICES):
        errors["unit"] = "Choose a unit from the list."
    elif unit and crop in PRODUCTS and unit not in units_for(crop):
        errors["unit"] = "That unit doesn't fit this product."

    def number(field, cast, low, high, message):
        raw = (data.get(field) or "").strip()
        if raw == "":
            return None
        try:
            value = cast(raw)
        except (ValueError, InvalidOperation):
            errors[field] = message
            return None
        if not (low <= value <= high):
            errors[field] = message
        return value

    qty = number("quantity", int, 1, 1_000_000, "Enter a whole number from 1 to 1 000 000.")
    price = number("price", Decimal, Decimal("0.01"), Decimal("100000"), "Enter a price above 0.")
    zig = number("price_zig", Decimal, Decimal("0"), Decimal("10000000"), "Enter a ZiG price, or leave it empty.")
    if price is not None and price.as_tuple().exponent < -2:
        errors["price"] = "Use at most 2 decimal places (cents)."

    province = data.get("province", "")
    if province and province not in PROVINCES:
        errors["province"] = "Choose a province from the list."
    district = (data.get("district") or "").strip()
    if len(district) > 60:
        errors["district"] = "Use 60 characters or fewer."
    delivery = data.get("delivery") or "both"
    if delivery not in dict(DELIVERY_CHOICES):
        errors["delivery"] = "Choose how buyers get it."
    description = (data.get("description") or "").strip()
    if len(description) > 500:
        errors["description"] = "Keep the description under 500 characters."
    variety = (data.get("variety") or "").strip()
    if len(variety) > 60:
        errors["variety"] = "Use 60 characters or fewer."

    available = parse_date(data.get("available") or "") or today
    if available < today:
        errors["available"] = "The ready date can't be in the past."
    elif (available - today).days > READY_WINDOW_DAYS:
        errors["available"] = f"You can list up to {READY_WINDOW_DAYS} days before it's ready. Please come back closer to the date."
    harvested = parse_date(data.get("harvested_on") or "")
    if data.get("harvested_on") and not harvested:
        errors["harvested_on"] = "Choose a date."
    elif harvested and harvested > today:
        errors["harvested_on"] = "The harvest date can't be in the future."
    elif harvested and (today - harvested).days > 60:
        errors["harvested_on"] = "That harvest date is more than 60 days ago."
    if available > today:
        harvested = None                              # coming soon: not harvested yet
    sell_today = str(data.get("sell_today", "")).lower() in ("1", "true", "on") and available <= today

    photos = files.getlist("photos") if files else []
    if len(photos) > MAX_PHOTOS:
        errors["photos"] = f"Up to {MAX_PHOTOS} photos."

    if not draft:                                     # publishing needs everything
        for field, value, message in [("quantity", qty, "Enter how much you have."), ("price", price, "Enter your price per unit."),
                                      ("unit", unit, "Choose a unit."), ("province", province, "Choose your province."),
                                      ("district", district, "Enter your district or area.")]:
            if not value and field not in errors:
                errors[field] = message

    out.update(crop=crop, unit=unit or units_for(crop)[0], quantity=qty or 0, price_usd=price or Decimal("0"),
               price_zig=zig, province=province, district=district, delivery=delivery, description=description,
               variety=variety, available_from=available, harvested_on=harvested, sell_today=sell_today)
    return out, errors, photos


@allow("GET", "POST")
def listings(request):
    if request.method == "GET":
        qs = _market_queryset(request.GET)
        try:
            page = max(1, int(request.GET.get("page", 1)))
        except ValueError:
            page = 1
        count = qs.count()
        rows = list(qs[(page - 1) * PAGE_SIZE: page * PAGE_SIZE])        # LIMIT 12 OFFSET ...
        prices = market_cache()
        records = seller_records({l.farmer_id for l in rows})
        results = [listing_json(l, request, market=compare(l.price_usd, prices.get((l.crop, l.unit))), records=records)
                   for l in rows]
        return JsonResponse({"results": results, "count": count, "page": page,
                             "next": page + 1 if page * PAGE_SIZE < count else None})

    # POST: create a listing (multipart form, so photos can come too)
    if not request.user.is_authenticated:
        return json_error("Please log in to list produce.", status=401)
    if not request.user.can_sell:
        return json_error("Only farmer accounts can list produce.", status=403)
    over = throttle(request, "listing", 20, 86400, "You've added a lot of listings today. Please try again tomorrow.")
    if over:
        return over
    draft = request.POST.get("status") == "draft"
    cleaned, errors, uploads = _read_listing_form(request.POST, request.FILES, draft)
    cleaned_photos = []
    if not errors:
        for up in uploads:
            try:
                cleaned_photos.append(clean_photo(up))
            except PhotoError as e:
                errors["photos"] = str(e)
                break
    if errors:
        return json_error("Please check the form.", errors=errors)

    with transaction.atomic():                         # the listing and its photos are saved together, or not at all
        listing = Listing.objects.create(farmer=request.user, status=Listing.DRAFT if draft else Listing.ACTIVE,
                                         quantity_left=cleaned["quantity"], **cleaned)
        for i, f in enumerate(cleaned_photos):
            ListingPhoto.objects.create(listing=listing, image=f, position=i)
    return JsonResponse(listing_json(listing, request), status=201)


@allow("GET")
def listing_detail(request, listing_id):
    l = Listing.objects.select_related("farmer").prefetch_related("photos").filter(pk=listing_id).first()
    mine = bool(l and request.user.is_authenticated and l.farmer_id == request.user.id)
    staff = request.user.is_authenticated and request.user.is_staff
    if not l or (l.status in (Listing.DRAFT, Listing.HIDDEN) and not (mine or staff)):
        return json_error("This listing doesn't exist or was removed.", status=404)
    if l.status == Listing.ACTIVE and l.ready_in_days > READY_WINDOW_DAYS and not mine:
        return json_error("This listing isn't open yet.", status=404)

    records = seller_records([l.farmer_id])
    data = listing_json(l, request, records=records)
    f = l.farmer
    data.update(
        description=l.description, photos=photo_urls(l, request), is_mine=mine,
        sold_out=l.quantity_left < 1 or l.status == Listing.SOLD_OUT,
        farmer={**farmer_card(f, records), "member_since": f.date_joined.strftime("%Y-%m"),
                "verified_on": f.verified_farmer_on.isoformat() if f.is_verified_farmer and f.verified_farmer_on else None,
                "reviews": seller_reviews(f)},
    )
    open_ = Listing.objects.open().exclude(pk=l.pk)
    data["more_from_farmer"] = [{"id": x.id, "crop": x.crop, "variety": x.variety, "price_usd": float(x.price_usd), "unit": x.unit}
                                for x in open_.filter(farmer=f)[:3]]
    data["similar"] = [{"id": x.id, "crop": x.crop, "variety": x.variety, "price_usd": float(x.price_usd), "unit": x.unit,
                        "province": x.province, "district": x.district} for x in open_.filter(crop=l.crop).exclude(farmer=f)[:3]]
    return JsonResponse(data)


def _own_listing(request, listing_id):
    if not request.user.is_authenticated:
        return None, json_error("Please log in.", status=401)
    l = get_object_or_404(Listing, pk=listing_id)
    if l.farmer_id != request.user.id:
        return None, json_error("Only the farmer who listed this can change it.", status=403)
    return l, None


@allow("POST")
def mark_sold_out(request, listing_id):
    l, err = _own_listing(request, listing_id)
    if err:
        return err
    if l.status != Listing.ACTIVE:
        return json_error(f"This listing is {l.get_status_display().lower()}.", status=409)
    l.status = Listing.SOLD_OUT
    l.save(update_fields=["status", "updated_at"])
    return JsonResponse({"id": l.id, "status": l.status})


@allow("POST")
def publish(request, listing_id):
    """Draft -> on the market, after the same checks as publishing straight away."""
    l, err = _own_listing(request, listing_id)
    if err:
        return err
    if l.status != Listing.DRAFT:
        return json_error("Only drafts can be published.", status=409)
    missing = {k: v for k, v in {"quantity": l.quantity, "price": l.price_usd, "province": l.province,
                                 "district": l.district}.items() if not v}
    if missing:
        return json_error("Finish the listing before publishing.", errors={k: "Missing." for k in missing})
    if l.available_from < timezone.localdate():
        l.available_from = timezone.localdate()
    l.status = Listing.ACTIVE
    l.quantity_left = l.quantity
    l.save()
    return JsonResponse({"id": l.id, "status": l.status})


@allow("POST")
def report_listing(request, listing_id):
    """Anyone logged in can flag a listing for staff. Limits stop one person flooding staff."""
    if not request.user.is_authenticated:
        return json_error("Please log in to report a listing. It helps us keep the market honest.", status=401)
    me = request.user
    if rate_limited(f"report:{me.id}", REPORTS_PER_DAY, 86400):
        return json_error("You've sent a lot of reports today. Staff will look at them; please try again tomorrow.", status=429)
    l = Listing.objects.filter(pk=listing_id).exclude(status=Listing.DRAFT).first()
    if not l or l.farmer_id == me.id:
        return json_error("This listing doesn't exist, or it's yours.", status=404)
    data, err = read_json(request)
    if err:
        return err
    reason = data.get("reason")
    details = str(data.get("details") or "").strip()
    errors = {}
    if reason not in dict(ListingReport.REASONS):
        errors["reason"] = "Choose what is wrong."
    if len(details) > 300:
        errors["details"] = "Keep it under 300 characters."
    if errors:
        return json_error("Please check the form.", errors=errors)
    try:
        with transaction.atomic():
            ListingReport.objects.create(listing=l, reporter=me, reason=reason, details=details)
    except IntegrityError:
        return json_error("You've already reported this listing. Staff will look at it.", status=409)
    return JsonResponse({"ok": True}, status=201)


@allow("GET")
def my_listings(request):
    if not request.user.is_authenticated:
        return json_error("Please log in.", status=401)
    qs = Listing.objects.filter(farmer=request.user).exclude(status=Listing.HIDDEN) \
        .select_related("farmer").prefetch_related("photos").order_by("-created_at") \
        .annotate(pending_n=Count("orders", filter=Q(orders__status="pending")))
    records = seller_records([request.user.id])
    results = []
    for l in qs:
        d = listing_json(l, request, records=records)
        d["status"] = Listing.SOLD_OUT if (l.status == Listing.ACTIVE and l.quantity_left < 1) else l.status
        d["pending_offers"] = l.pending_n
        results.append(d)
    return JsonResponse({"results": results})
