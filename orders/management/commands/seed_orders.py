"""
python manage.py seed_orders

Sample buyers, buyer requests (501-505), offers and orders (9001...) and ratings, so
My account and the farmers' track records look real while testing. Dates count from today.
Safe to run again: does nothing if any order already exists. Needs seed_demo and seed_market first.
Sample buyers can't log in (no password).
"""
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.utils import timezone

from accounts.models import User
from buyer_requests.models import BuyerRequest
from listings.models import Listing
from orders.models import Order, Rating

# key: (phone, name, business_type)
BUYERS = {
    "freshmart": ("+263712555001", "FreshMart, Avondale", "Supermarket"),
    "kuchikwata": ("+263712555002", "Kuchikwata Restaurant", "Restaurant"),
    "maichipo": ("+263712555003", "Chipo Mutasa", ""),
    "mzilikazi": ("+263712555004", "Mzilikazi High School", "School"),
    "farai": ("+263712555005", "Farai's Greengrocer", "Shop"),
    "banda": ("+263712555006", "James Banda", ""),
    "masvingo": ("+263712555007", "Masvingo traders group", "Traders"),
    "meikles": ("+263712555008", "Garden Hotel, Harare", "Hotel"),
}

# id, buyer, crop, qty, unit, province, district, needed_by(+days), repeat, max price, delivery, note, created(-days)
REQUESTS = [
    (501, "freshmart", "Tomatoes", 300, "crate", "Harare", "Avondale", 3, "weekly", "6.80", "delivery",
     "Firm, grade A only. Delivery to our Avondale store before 8 am.", 4),
    (502, "mzilikazi", "Sugar beans", 1000, "kg", "Bulawayo", "Mzilikazi", 10, "once", None, "either",
     "For the boarding kitchen. Clean, dry beans.", 3),
    (503, "kuchikwata", "Potatoes", 40, "pocket_15kg", "Harare", "Borrowdale", 2, "weekly", "9.50", "delivery", "", 1),
    (504, "masvingo", "Maize", 60, "tonne", "Masvingo", "Masvingo town", 19, "once", "300", "pickup",
     "We collect with our own trucks.", 6),
    (505, "tendai", "Maize", 30, "bag_50kg", "Mashonaland East", "Murehwa", 12, "monthly", "15", "delivery",
     "Dry white maize for farm workers' rations.", 1),
]


class Command(BaseCommand):
    help = "Sample buyers, requests, offers, orders and ratings."

    @transaction.atomic
    def handle(self, *args, **opts):
        if Order.objects.exists():
            self.stdout.write("  orders already exist: nothing to do")
            return
        tendai = User.objects.filter(phone="+263771234567").first()
        rudo = User.objects.filter(phone="+263712345678").first()
        if not tendai or not Listing.objects.filter(pk=101).exists():
            self.stderr.write("Run `python manage.py seed_demo` and `python manage.py seed_market` first.")
            return
        now, today = timezone.now(), timezone.localdate()
        ago = lambda days, hours=0: now - timedelta(days=days, hours=hours)  # noqa: E731

        people = {"tendai": tendai, "rudo": rudo}
        for key, (phone, name, kind) in BUYERS.items():
            people[key] = User.objects.filter(phone=phone).first() or User.objects.create_user(
                phone, None, name=name, role="buyer", business_type=kind, phone_verified_at=now,
                date_joined=ago(200))
        farmer = lambda phone: User.objects.get(phone=phone)  # noqa: E731

        # ---- Buyer requests
        for (pk, who, crop, qty, unit, prov, dist, need, repeat, mx, delivery, note, created) in REQUESTS:
            BuyerRequest.objects.create(pk=pk, buyer=people[who], crop=crop, quantity=qty, unit=unit, province=prov,
                                        district=dist, needed_by=today + timedelta(days=need), repeat=repeat,
                                        max_price_usd=Decimal(mx) if mx else None, delivery=delivery, note=note,
                                        created_at=ago(created))

        def order(pk, listing=None, request=None, buyer=None, farmer_=None, qty=1, delivery="pickup", status="pending",
                  days=0, message="", price=None, variety=None, ready=None, done_days=None):
            if listing:
                l = Listing.objects.get(pk=listing)
                buyer_, farmer_, by = people[buyer] if isinstance(buyer, str) else buyer, l.farmer, Order.BY_BUYER
                crop, unit, variety, price = l.crop, l.unit, variety or l.variety, price or l.price_usd
            else:
                r = BuyerRequest.objects.get(pk=request)
                buyer_, by = r.buyer, Order.BY_FARMER
                crop, unit = r.crop, r.unit
            o = Order.objects.create(
                pk=pk, listing_id=listing, request_id=request, proposed_by=by, farmer=farmer_, buyer=buyer_,
                crop=crop, variety=variety or "", unit=unit, price_usd=Decimal(str(price)), quantity=qty,
                delivery=delivery, message=message, status=status, created_at=ago(days, 2),
                ready_on=today + timedelta(days=ready) if ready is not None else None,
                accepted_at=ago(days) if status in ("accepted", "completed") else None,
                completed_at=ago(done_days if done_days is not None else max(days - 2, 0)) if status == "completed" else None)
            return o

        def rate(o, by, stars, comment=""):
            other = o.buyer if by == o.farmer else o.farmer
            Rating.objects.create(order=o, by_user=by, for_user=other, stars=stars, comment=comment,
                                  created_at=o.completed_at + timedelta(hours=3))

        # ---- Offers on Tendai's tomatoes (listing 101: 120 crates, 36 already sold -> 84 left)
        order(9001, listing=101, buyer="freshmart", qty=20, delivery="delivery", message="Can you deliver on Friday morning?")
        order(9002, listing=101, buyer="kuchikwata", qty=8, days=1)
        order(9003, listing=101, buyer="maichipo", qty=70, days=1, message="I can take a big load if the price is right.")
        order(9004, listing=101, buyer="mzilikazi", qty=16, delivery="delivery", status="accepted", days=2)
        o = order(9005, listing=101, buyer="farai", qty=20, status="completed", days=6, done_days=4)
        rate(o, o.buyer, 5, "Fresh and well packed.")
        order(9006, listing=101, buyer="banda", qty=2, delivery="delivery", status="declined", days=3)

        # ---- Tendai as a buyer
        order(9101, listing=115, buyer="tendai", qty=40, status="accepted", days=1, message="For a family function on Saturday.")
        order(9102, listing=116, buyer="tendai", qty=10, delivery="delivery")
        # A farmer offering to supply PART of Tendai's request 505 (Tendai decides)
        order(9201, request=505, farmer_=farmer("+263772000120"), qty=20, delivery="delivery", price="14.00",
              variety="White, dry", ready=3, message="I can bring 20 bags on Saturday. The other 10 maybe next month.")

        # ---- Rudo (the demo buyer account)
        if rudo:
            order(9301, listing=106, buyer="rudo", qty=5, delivery="delivery", message="For my shop in Mutare. Can you deliver?")
            o = order(9302, listing=107, buyer="rudo", qty=10, status="completed", days=8, done_days=6)
            rate(o, o.buyer, 4, "Sweet oranges, a day late.")
            rate(o, o.farmer, 5)

        # ---- Past sales, so sample farmers have a track record (within what each listing has already sold)
        history = [  # listing, buyer, qty, stars, comment, days ago
            (115, "meikles", 20, 5, "Healthy birds, good weight. Delivered on time.", 12),
            (116, "freshmart", 15, 5, "Every tray was full and clean.", 9),
            (116, "meikles", 10, 4, "", 15),
            (104, "masvingo", 8, 5, "Dry maize, honest weights.", 25),
            (105, "mzilikazi", 150, 4, "Good beans, some small stones.", 14),
            (107, "farai", 40, 5, "Sweet oranges.", 10),
            (111, "mzilikazi", 180, 5, "", 30),
            (114, "masvingo", 600, 3, "", 40),
        ]
        pk = 9401
        for listing, who, qty, stars, comment, days in history:
            o = order(pk, listing=listing, buyer=who, qty=qty, status="completed", days=days)
            rate(o, o.buyer, stars, comment)
            pk += 1

        # ---- Accepted supply offers that fill part of the requests
        supply = [  # request, farmer phone, qty, price
            (501, "+263772000113", 80, "6.60"), (501, "+263772000119", 60, "6.50"), (501, "+263772000110", 40, "6.80"),
            (502, "+263772000105", 250, "2.20"),
            (504, "+263772000104", 12, "295"), (504, "+263772000112", 10, "290"),
        ]
        for request, phone, qty, price in supply:
            order(pk, request=request, farmer_=farmer(phone), qty=qty, price=price, status="accepted", days=2,
                  variety="As requested", ready=2,
                  delivery="pickup" if BuyerRequest.objects.get(pk=request).delivery == "pickup" else "delivery")
            pk += 1

        self._reset_id_counters()
        self.stdout.write(self.style.SUCCESS(
            f"  {len(BUYERS)} sample buyers, {len(REQUESTS)} requests, {Order.objects.count()} offers and orders, "
            f"{Rating.objects.count()} ratings"))

    def _reset_id_counters(self):
        """We chose the ids; tell PostgreSQL so new rows don't clash. (SQLite does this itself.)"""
        if connection.vendor == "postgresql":
            from django.core.management.color import no_style
            with connection.cursor() as c:
                for sql in connection.ops.sequence_reset_sql(no_style(), [BuyerRequest, Order]):
                    c.execute(sql)
