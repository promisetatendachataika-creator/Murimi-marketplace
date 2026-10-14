"""
python manage.py seed_market

Fills an EMPTY market with realistic sample listings, farmers and Mbare prices, so the
site never looks empty while testing. Dates are counted from today. Safe to run again:
it does nothing if listings already exist. Sample farmers can't log in (no password).
"""
import shutil
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone

from accounts.models import User
from listings.models import Listing, ListingPhoto
from prices.models import PriceReport

# (phone, name, verified, months on Murimi)
FARMERS = {
    "Rudo C.": ("+263772000102", "Rudo Chiweshe", True, 12), "Blessing N.": ("+263772000103", "Blessing Nyathi", False, 2),
    "Chipo Farms": ("+263772000104", "Chipo Farms", True, 30), "Farai D.": ("+263772000105", "Farai Dube", True, 9),
    "Mai Ropafadzo": ("+263772000106", "Mai Ropafadzo", True, 6), "Tinashe G.": ("+263772000107", "Tinashe Gumbo", False, 3),
    "Kuda S.": ("+263772000108", "Kuda Sibanda", True, 14), "Sipho Ndlovu": ("+263772000109", "Sipho Ndlovu", True, 10),
    "Nomsa K.": ("+263772000110", "Nomsa Khumalo", False, 1), "Thandeka M.": ("+263772000111", "Thandeka Moyo", True, 8),
    "Garikai T.": ("+263772000112", "Garikai Tapfuma", True, 11), "Tatenda R.": ("+263772000113", "Tatenda Rusere", True, 7),
    "Memory Z.": ("+263772000114", "Memory Zhou", False, 4), "Nyasha P.": ("+263772000115", "Nyasha Pfende", True, 23),
    "Mai Tafadzwa": ("+263772000116", "Mai Tafadzwa", True, 28), "Sibusiso M.": ("+263772000117", "Sibusiso Mpofu", False, 5),
    "Chiedza F.": ("+263772000118", "Chiedza Fambisai", True, 13), "Tonderai K.": ("+263772000119", "Tonderai Kamba", True, 15),
    "Rutendo B.": ("+263772000120", "Rutendo Banda", False, 2),
}

# id, farmer, crop, variety, qty, left, unit, price, province, district, ready(+days), harvested(-days), delivery, sell_today, created(-days), description
LISTINGS = [
    (101, "Tendai M.", "Tomatoes", "Roma, grade A", 120, 84, "crate", "6.50", "Mashonaland East", "Murehwa", 0, 3, "both", False, 2,
     "Firm Roma tomatoes, picked and packed in clean crates of about 30 kg. Good for supermarkets and restaurants: even size, no cracks. I can deliver within 40 km of Murehwa, or you can collect from the farm on the Mutoko road."),
    (102, "Rudo C.", "Potatoes", "BP1", 200, 200, "pocket_15kg", "9.50", "Manicaland", "Nyanga", 0, 4, "pickup", False, 2,
     "BP1 potatoes from Nyanga, washed and graded. Packed in 15 kg pockets. Collection from the farm only."),
    (103, "Blessing N.", "Tomatoes", "Star 9003", 40, 40, "crate", "4.50", "Harare", "Domboshava", 0, 1, "delivery", True, 0,
     "Ripe tomatoes that must go today. Good for sauce, relish and street vendors. Lower price for a quick sale."),
    (104, "Chipo Farms", "Maize", "White, dry", 30, 22, "tonne", "295", "Mashonaland West", "Chinhoyi", 0, 86, "pickup", False, 5,
     "Dry white maize, moisture checked. Stored in a clean shed. Minimum 1 tonne per buyer."),
    (105, "Farai D.", "Sugar beans", "Nua 45", 800, 650, "kg", "2.30", "Midlands", "Gokwe", 0, 16, "both", False, 4, ""),
    (106, "Mai Ropafadzo", "Avocados", "Hass", 60, 60, "crate", "11.00", "Manicaland", "Chipinge", 0, 3, "delivery", False, 2, ""),
    (107, "Tinashe G.", "Citrus", "Valencia oranges", 90, 35, "crate", "6.80", "Masvingo", "Chiredzi", 0, 8, "both", False, 6, ""),
    (108, "Kuda S.", "Maize", "Green mealies", 50, 50, "bag_50kg", "14.00", "Mashonaland Central", "Bindura", 0, 1, "pickup", True, 0, ""),
    (109, "Sipho Ndlovu", "Potatoes", "Mondial", 80, 80, "pocket_15kg", "8.20", "Matabeleland South", "Gwanda", 0, 5, "both", False, 3, ""),
    (110, "Nomsa K.", "Tomatoes", "Roma", 25, 25, "crate", "7.50", "Bulawayo", "Umguza", 0, 3, "delivery", False, 2, ""),
    (111, "Thandeka M.", "Sugar beans", "Speckled", 300, 120, "kg", "1.90", "Matabeleland North", "Lupane", 0, 19, "pickup", False, 10, ""),
    (112, "Garikai T.", "Citrus", "Lemons", 40, 40, "crate", "5.00", "Mashonaland East", "Mutoko", 0, 2, "both", False, 1, ""),
    (113, "Tatenda R.", "Tobacco", "Flue-cured, leaf grade", 2400, 2400, "kg", "3.10", "Mashonaland West", "Karoi", 0, 24, "pickup", False, 4, ""),
    (114, "Memory Z.", "Cotton", "Seed cotton, grade A", 1500, 900, "kg", "0.45", "Midlands", "Gokwe", 0, 29, "pickup", False, 8, ""),
    (115, "Nyasha P.", "Broilers", "Live, about 2 kg each", 300, 240, "bird", "5.00", "Harare", "Ruwa", 0, 2, "both", False, 2,
     "Healthy broilers, about 2 kg live weight, raised on commercial feed. Vaccinated. Collect in your own crates or we deliver in Harare east."),
    (116, "Mai Tafadzwa", "Eggs", "Large, brown", 120, 95, "tray_30", "4.20", "Mashonaland East", "Marondera", 0, 1, "delivery", False, 1,
     "Large brown eggs collected every morning. Delivered in trays of 30 to shops and restaurants in Marondera and Harare."),
    (117, "Sibusiso M.", "Eggs", "Mixed sizes", 40, 40, "tray_30", "3.80", "Bulawayo", "Cowdray Park", 0, 0, "pickup", False, 0, ""),
    (118, "Chiedza F.", "Broilers", "Live, will be 6 weeks old", 500, 500, "bird", "5.20", "Mashonaland West", "Norton", 6, None, "both", False, 0,
     "Our next batch reaches 6 weeks on the ready date. Reserve now for weddings, funerals and functions."),
    (119, "Tonderai K.", "Tomatoes", "Roma, still on the vine", 200, 200, "crate", "6.00", "Manicaland", "Mutasa", 9, None, "pickup", False, 1,
     "Roma tomatoes still on the vine, first picking expected on the ready date. Reserve now and I will confirm two days before."),
    (120, "Rutendo B.", "Maize", "Green mealies", 80, 80, "bag_50kg", "13.00", "Mashonaland East", "Goromonzi", 13, None, "both", False, 0, ""),
]
DRAFTS = [(121, "Tendai M.", "Potatoes", "BP1", 60, 60, "pocket_15kg", "9.00", "Mashonaland East", "Murehwa", 10, None, "pickup", False, 0, "")]

# crop, unit, usd, days ago, market   (sample prices: replace with real Mbare reports in the admin)
PRICES = [
    ("Tomatoes", "crate", "7.00", 1, "Mbare Musika"), ("Potatoes", "pocket_15kg", "9.00", 1, "Mbare Musika"),
    ("Maize", "bag_50kg", "16.00", 2, "Mbare Musika"), ("Maize", "tonne", "310", 12, "GMB floor"),
    ("Sugar beans", "kg", "2.10", 1, "Mbare Musika"), ("Citrus", "crate", "6.00", 2, "Mbare Musika"),
    ("Avocados", "crate", "12.00", 3, "Mbare Musika"), ("Broilers", "bird", "5.50", 1, "Mbare Musika"),
    ("Eggs", "tray_30", "4.50", 1, "Mbare Musika"),
]


class Command(BaseCommand):
    help = "Fill an empty market with sample listings, farmers and prices."

    def handle(self, *args, **opts):
        today = timezone.localdate()
        if not PriceReport.objects.exists():
            for crop, unit, usd, ago, market in PRICES:
                PriceReport.objects.create(crop=crop, unit=unit, price_usd=Decimal(usd), market=market,
                                           date=today - timedelta(days=ago), note="Sample price for testing")
            self.stdout.write(self.style.SUCCESS(f"  {len(PRICES)} sample market prices"))
        if Listing.objects.exists():
            self.stdout.write("  listings already exist: nothing to do")
            return

        tendai = User.objects.filter(phone="+263771234567").first()
        if not tendai:
            self.stderr.write("Run `python manage.py seed_demo` first (creates Tendai).")
            return
        people = {"Tendai M.": tendai}
        for short, (phone, name, verified, months) in FARMERS.items():
            u = User.objects.filter(phone=phone).first() or User.objects.create_user(
                phone, None, name=name, role="farmer", phone_verified_at=timezone.now(),
                is_verified_farmer=verified, verified_farmer_on=today - timedelta(days=30 * months - 20) if verified else None,
                date_joined=timezone.now() - timedelta(days=30 * months))
            people[short] = u

        now = timezone.now()
        for status, rows in ((Listing.ACTIVE, LISTINGS), (Listing.DRAFT, DRAFTS)):
            for (pk, who, crop, variety, qty, left, unit, price, prov, dist, ready, harv, delivery, sell_today, created, desc) in rows:
                created_at = now if sell_today else now - timedelta(days=created, hours=pk % 7)
                Listing.objects.create(
                    pk=pk, farmer=people[who], crop=crop, variety=variety, quantity=qty, quantity_left=left, unit=unit,
                    price_usd=Decimal(price), province=prov, district=dist, available_from=today + timedelta(days=ready),
                    harvested_on=today - timedelta(days=harv) if harv is not None else None, delivery=delivery,
                    sell_today=sell_today, description=desc, status=status, created_at=created_at)
        self._reset_id_counter()

        # Three sample photos for Tendai's tomatoes (copied from the static sample images)
        src = Path(settings.BASE_DIR) / "web" / "static" / "web" / "img" / "sample"
        listing = Listing.objects.get(pk=101)
        for i in range(3):
            path = src / f"listing-101-{i + 1}.webp"
            if path.exists():
                with path.open("rb") as fh:
                    ListingPhoto.objects.create(listing=listing, position=i, image=File(fh, name=f"sample-101-{i + 1}.webp"))
        self.stdout.write(self.style.SUCCESS(f"  {len(LISTINGS)} sample listings, 1 draft, {len(FARMERS)} sample farmers"))

    def _reset_id_counter(self):
        """We chose the ids (101...); tell PostgreSQL so new listings don't clash. (SQLite does this itself.)"""
        if connection.vendor == "postgresql":
            from django.core.management.color import no_style
            with connection.cursor() as c:
                for sql in connection.ops.sequence_reset_sql(no_style(), [Listing]):
                    c.execute(sql)
