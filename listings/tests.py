"""
Listings and market-price tests. Run:  python manage.py test listings
"""
import io
import json
import shutil
import tempfile
from datetime import timedelta
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.utils import timezone
from PIL import Image

from accounts.models import User
from prices.models import PriceReport, compare

from .models import Listing, ListingPhoto

TMP_MEDIA = tempfile.mkdtemp()


def photo_bytes(fmt="JPEG", size=(2400, 1500), gps=False):
    img = Image.new("RGB", size, (200, 40, 40))
    buf = io.BytesIO()
    kwargs = {}
    if gps and fmt == "JPEG":
        exif = Image.Exif()
        exif[0x8825] = {1: "S", 2: (17.0, 49.0, 0.0)}           # a GPS location, like a phone adds
        kwargs["exif"] = exif.tobytes()
    img.save(buf, fmt, **kwargs)
    return buf.getvalue()


def make_listing(farmer, **kw):
    data = dict(crop="Tomatoes", variety="Roma", quantity=50, quantity_left=50, unit="crate", price_usd=Decimal("6.50"),
                province="Harare", district="Ruwa", delivery="both")
    data.update(kw)
    return Listing.objects.create(farmer=farmer, **data)


class Browser:
    """A logged-in browser with CSRF checks ON."""

    def __init__(self, user=None):
        self.c = Client(enforce_csrf_checks=True)
        self.c.get("/")
        if user:
            self.c.force_login(user)

    def post(self, url, data=None, files=None):
        token = self.c.cookies["csrftoken"].value
        return self.c.post(url, {**(data or {}), **(files or {})}, HTTP_X_CSRFTOKEN=token)

    def get(self, url, params=None):
        return self.c.get(url, params or {})


@override_settings(MEDIA_ROOT=TMP_MEDIA)
class ListingTestsBase(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.farmer = User.objects.create_user("0771234567", "murimi2026", name="Tendai Moyo", role="both", is_verified_farmer=True)
        self.other = User.objects.create_user("0772000102", "murimi2026", name="Rudo Chiweshe", role="farmer")
        self.buyer = User.objects.create_user("0712345678", "murimi2026", name="Rudo Buyer", role="buyer")


class MarketTests(ListingTestsBase):
    def test_market_shows_only_open_listings(self):
        today = timezone.localdate()
        visible = make_listing(self.farmer)
        make_listing(self.farmer, status=Listing.DRAFT)
        make_listing(self.farmer, status=Listing.HIDDEN)
        make_listing(self.farmer, status=Listing.SOLD_OUT)
        make_listing(self.farmer, quantity_left=0)
        make_listing(self.farmer, available_from=today + timedelta(days=20))          # more than 2 weeks away
        make_listing(self.farmer, sell_today=True, created_at=timezone.now() - timedelta(days=1))   # yesterday's "sell today"
        ids = [x["id"] for x in Browser().get("/api/listings/").json()["results"]]
        self.assertEqual(ids, [visible.id])

    def test_filters_and_sorting(self):
        a = make_listing(self.farmer, price_usd=Decimal("7.00"))
        b = make_listing(self.other, price_usd=Decimal("5.00"), province="Manicaland")
        c = make_listing(self.other, crop="Eggs", unit="tray_30", price_usd=Decimal("4.00"))
        get = lambda **p: [x["id"] for x in Browser().get("/api/listings/", p).json()["results"]]
        self.assertEqual(get(crop="Tomatoes", sort="price_asc"), [b.id, a.id])
        self.assertEqual(get(province="Manicaland"), [b.id])
        self.assertEqual(sorted(get(max_price="5")), sorted([b.id, c.id]))
        self.assertEqual(get(sort="price_desc")[0], a.id)

    def test_pages_of_12(self):
        for _ in range(14):
            make_listing(self.farmer)
        p1 = Browser().get("/api/listings/").json()
        p2 = Browser().get("/api/listings/", {"page": 2}).json()
        self.assertEqual((p1["count"], len(p1["results"]), p1["next"]), (14, 12, 2))
        self.assertEqual((len(p2["results"]), p2["next"]), (2, None))

    def test_one_market_page_costs_a_fixed_number_of_queries(self):
        for _ in range(10):
            make_listing(self.farmer)
        with self.assertNumQueries(6):   # count, rows+farmer, photos, prices, completed orders, ratings: not one per card
            Browser().get("/api/listings/")

    def test_no_phone_numbers_in_listings(self):
        make_listing(self.farmer)
        body = Browser().get("/api/listings/").content.decode()
        self.assertNotIn("263771234567", body)

    def test_stats_for_the_map(self):
        make_listing(self.farmer)
        make_listing(self.other, province="Masvingo")
        s = Browser().get("/api/stats/").json()
        self.assertEqual(s["listings"], 2)
        self.assertEqual(s["verified_farmers"], 1)
        self.assertEqual(s["by_province"], {"Harare": 1, "Masvingo": 1})


class FairPriceTests(ListingTestsBase):
    def test_bands_and_stale_prices(self):
        today = timezone.localdate()
        fresh = PriceReport.objects.create(crop="Tomatoes", unit="crate", price_usd=Decimal("7.00"), date=today - timedelta(days=1))
        self.assertEqual(compare(Decimal("6.00"), fresh)["band"], "below")
        self.assertEqual(compare(Decimal("7.20"), fresh)["band"], "at")          # within 5%
        self.assertEqual(compare(Decimal("8.00"), fresh)["band"], "above")
        old = PriceReport.objects.create(crop="Maize", unit="tonne", price_usd=Decimal("310"), date=today - timedelta(days=12))
        self.assertTrue(compare(Decimal("295"), old)["stale"])

    def test_best_value_sort_puts_unpriced_last(self):
        PriceReport.objects.create(crop="Tomatoes", unit="crate", price_usd=Decimal("7.00"))
        cheap = make_listing(self.farmer, price_usd=Decimal("5.00"))
        dear = make_listing(self.farmer, price_usd=Decimal("8.00"))
        unpriced = make_listing(self.farmer, crop="Cotton", unit="kg", price_usd=Decimal("0.40"))
        ids = [x["id"] for x in Browser().get("/api/listings/", {"sort": "fair"}).json()["results"]]
        self.assertEqual(ids, [cheap.id, dear.id, unpriced.id])

    def test_meta_has_latest_prices(self):
        PriceReport.objects.create(crop="Eggs", unit="tray_30", price_usd=Decimal("4.50"), date=timezone.localdate() - timedelta(days=3))
        PriceReport.objects.create(crop="Eggs", unit="tray_30", price_usd=Decimal("4.20"))
        prices = Browser().get("/api/meta/").json()["prices"]
        self.assertEqual([p["usd"] for p in prices if p["crop"] == "Eggs"], [4.2])


class CreateListingTests(ListingTestsBase):
    FORM = {"crop": "Potatoes", "variety": "Mondial", "quantity": "150", "unit": "pocket_15kg", "price": "8.50",
            "price_zig": "230", "province": "Manicaland", "district": "Nyanga", "delivery": "both", "description": "Washed."}

    def test_publish_with_photos(self):
        files = {"photos": [SimpleUploadedFile("a.jpg", photo_bytes(gps=True), "image/jpeg"),
                            SimpleUploadedFile("b.png", photo_bytes("PNG", (300, 200)), "image/png")]}
        r = Browser(self.farmer).post("/api/listings/", self.FORM, files)
        self.assertEqual(r.status_code, 201, r.content)
        listing = Listing.objects.get(pk=r.json()["id"])
        self.assertEqual((listing.status, listing.quantity_left, listing.price_zig), ("active", 150, Decimal("230")))
        self.assertEqual(listing.farmer, self.farmer)
        photos = list(listing.photos.all())
        self.assertEqual(len(photos), 2)
        with Image.open(photos[0].image.path) as img:
            self.assertEqual(img.format, "JPEG")
            self.assertLessEqual(max(img.size), 1600)                         # made smaller
            self.assertNotIn(0x8825, img.getexif())                           # GPS location removed

    def test_fake_photo_is_refused(self):
        files = {"photos": [SimpleUploadedFile("tomatoes.jpg", b"MZ this is really a program", "image/jpeg")]}
        r = Browser(self.farmer).post("/api/listings/", self.FORM, files)
        self.assertEqual(r.status_code, 400)
        self.assertIn("photos", r.json()["errors"])
        self.assertFalse(Listing.objects.exists())                            # nothing half-saved

    def test_gif_is_refused_even_if_called_jpg(self):
        buf = io.BytesIO()
        Image.new("RGB", (50, 50)).save(buf, "GIF")
        files = {"photos": [SimpleUploadedFile("x.jpg", buf.getvalue(), "image/jpeg")]}
        r = Browser(self.farmer).post("/api/listings/", self.FORM, files)
        self.assertIn("JPG, PNG or WebP", r.json()["errors"]["photos"])

    def test_errors_per_field(self):
        bad = {**self.FORM, "crop": "Gold", "quantity": "0", "price": "-1", "district": "",
               "available": (timezone.localdate() + timedelta(days=30)).isoformat()}
        errors = Browser(self.farmer).post("/api/listings/", bad).json()["errors"]
        for f in ["crop", "quantity", "price", "district", "available"]:
            self.assertIn(f, errors)

    def test_unit_must_fit_product(self):
        r = Browser(self.farmer).post("/api/listings/", {**self.FORM, "crop": "Eggs", "unit": "tonne"})
        self.assertIn("unit", r.json()["errors"])

    def test_draft_can_be_half_finished_and_published_later(self):
        b = Browser(self.farmer)
        r = b.post("/api/listings/", {"crop": "Eggs", "unit": "tray_30", "status": "draft"})
        self.assertEqual(r.status_code, 201)
        draft_id = r.json()["id"]
        self.assertEqual(Browser().get(f"/api/listings/{draft_id}/").status_code, 404)    # hidden from others
        self.assertEqual(b.post(f"/api/listings/{draft_id}/publish/").status_code, 400)    # not finished yet
        Listing.objects.filter(pk=draft_id).update(quantity=10, price_usd=Decimal("4"), province="Harare", district="Mbare")
        self.assertEqual(b.post(f"/api/listings/{draft_id}/publish/").json()["status"], "active")

    def test_who_may_sell(self):
        self.assertEqual(Browser().post("/api/listings/", self.FORM).status_code, 401)
        self.assertEqual(Browser(self.buyer).post("/api/listings/", self.FORM).status_code, 403)

    def test_coming_soon_has_no_harvest_date(self):
        ready = (timezone.localdate() + timedelta(days=9)).isoformat()
        r = Browser(self.farmer).post("/api/listings/", {**self.FORM, "available": ready, "harvested_on": timezone.localdate().isoformat()})
        self.assertEqual((r.json()["ready_in_days"], r.json()["harvested_on"]), (9, None))


class OwnerActionTests(ListingTestsBase):
    def test_only_the_owner_can_mark_sold_out(self):
        l = make_listing(self.farmer)
        self.assertEqual(Browser(self.other).post(f"/api/listings/{l.id}/sold-out/").status_code, 403)
        self.assertEqual(Browser(self.farmer).post(f"/api/listings/{l.id}/sold-out/").status_code, 200)
        self.assertEqual(Browser().get("/api/listings/").json()["count"], 0)

    def test_my_listings_include_drafts_but_not_other_peoples(self):
        make_listing(self.farmer)
        make_listing(self.farmer, status=Listing.DRAFT)
        make_listing(self.other)
        rows = Browser(self.farmer).get("/api/me/listings/").json()["results"]
        self.assertEqual(sorted(r["status"] for r in rows), ["active", "draft"])

    def test_detail_shows_photos_and_is_mine(self):
        l = make_listing(self.farmer)
        ListingPhoto.objects.create(listing=l, image=SimpleUploadedFile("p.jpg", photo_bytes(size=(100, 80)), "image/jpeg"))
        d = Browser(self.farmer).get(f"/api/listings/{l.id}/").json()
        self.assertTrue(d["is_mine"])
        self.assertEqual(len(d["photos"]), 1)
        self.assertNotIn("phone", json.dumps(d["farmer"]))


class SeedMarketTests(TestCase):
    @override_settings(MEDIA_ROOT=TMP_MEDIA)
    def test_seed_market(self):
        from io import StringIO

        from django.core.management import call_command
        call_command("seed_demo", stdout=StringIO())
        call_command("seed_market", stdout=StringIO())
        call_command("seed_market", stdout=StringIO())                       # safe to repeat
        self.assertEqual(Listing.objects.filter(status="active").count(), 20)
        self.assertEqual(Listing.objects.get(pk=101).farmer.username, "tendai")
        self.assertEqual(Listing.objects.get(pk=101).photos.count(), 3)
        self.assertGreater(Listing.objects.create(farmer=User.objects.get(username="tendai"), crop="Eggs", unit="tray_30",
                                                  quantity=1, quantity_left=1, price_usd=1).pk, 121)   # ids continue after the samples


class ReportAndStaffTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()                    # rate-limit counts live in the cache
        self.farmer = User.objects.create_user("+263771111111", "pw-123456", name="Tendai Moyo", role="farmer")
        self.buyer = User.objects.create_user("+263712222222", "pw-123456", name="Rudo Chari", role="buyer")
        self.staff = User.objects.create_user("+263780000009", "pw-123456", name="Staff Person", role="", is_staff=True, is_superuser=True)
        self.listing = make_listing(self.farmer)

    def post(self, user, data, listing=None):
        b = Browser(user)
        c = b.c
        return c.post(f"/api/listings/{(listing or self.listing).id}/report/", json.dumps(data), content_type="application/json",
                      HTTP_X_CSRFTOKEN=c.cookies["csrftoken"].value)

    def test_report_needs_login_and_valid_reason(self):
        self.assertEqual(self.post(None, {"reason": "scam"}).status_code, 401)
        r = self.post(self.buyer, {"reason": "nonsense"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("reason", r.json()["errors"])
        self.assertEqual(self.post(self.buyer, {"reason": "scam", "details": "x" * 301}).status_code, 400)

    def test_report_saved_once_and_not_on_own_or_draft_listing(self):
        self.assertEqual(self.post(self.buyer, {"reason": "price", "details": "Too cheap"}).status_code, 201)
        self.assertEqual(self.post(self.buyer, {"reason": "price"}).status_code, 409)       # already reported
        self.assertEqual(self.post(self.farmer, {"reason": "scam"}).status_code, 404)      # not your own
        draft = make_listing(self.farmer, status="draft")
        self.assertEqual(self.post(self.buyer, {"reason": "scam"}, draft).status_code, 404)

    def test_report_limit_per_day(self):
        for i in range(10):
            l = make_listing(self.farmer)
            self.assertEqual(self.post(self.buyer, {"reason": "other"}, l).status_code, 201)
        self.assertEqual(self.post(self.buyer, {"reason": "other"}, make_listing(self.farmer)).status_code, 429)

    def test_staff_hide_and_close_action_and_dashboard(self):
        from .models import ListingReport
        self.post(self.buyer, {"reason": "scam"})
        c = Client()
        c.force_login(self.staff)
        home = c.get("/admin/")
        self.assertContains(home, "Reports waiting for a look")
        self.assertContains(home, "Prices out of date")
        r = c.post("/admin/listings/listingreport/", {"action": "hide_and_close", "_selected_action": [ListingReport.objects.get().pk]}, follow=True)
        self.assertEqual(r.status_code, 200)
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, "hidden")
        rep = ListingReport.objects.get()
        self.assertEqual((rep.status, rep.handled_by_id), ("done", self.staff.pk))
        self.assertEqual(Browser().get("/api/listings/").json()["count"], 0)

    def test_blocking_a_farmer_hides_listings_and_ends_session(self):
        farmer_browser = Browser(self.farmer)
        self.assertEqual(farmer_browser.get("/api/auth/me/").json()["user"]["id"], self.farmer.id)
        c = Client()
        c.force_login(self.staff)
        c.post("/admin/accounts/user/", {"action": "block_accounts", "_selected_action": [self.farmer.pk]}, follow=True)
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, "hidden")
        self.assertIsNone(farmer_browser.get("/api/auth/me/").json()["user"])         # logged out everywhere

    def test_staff_cannot_edit_agreed_orders(self):
        from orders.admin import OrderAdmin
        from orders.models import Order
        from django.contrib import admin as dj_admin
        ma = OrderAdmin(Order, dj_admin.site)

        class Req:
            user = self.staff
        self.assertFalse(ma.has_add_permission(Req))
        self.assertFalse(ma.has_delete_permission(Req))
        self.assertIn("price_usd", ma.get_readonly_fields(Req))


class StaffPageSurvivesMissingTableTests(TestCase):
    """If the code is updated but `migrate` hasn't been run, the staff page must explain, not crash."""

    def test_missing_table_shows_a_message(self):
        from django.db import DatabaseError
        from unittest import mock
        staff = User.objects.create_user("+263780000008", "pw-123456", name="Staff Person", role="", is_staff=True, is_superuser=True)
        c = Client()
        c.force_login(staff)
        with mock.patch("core.admin_dashboard.dashboard_items", side_effect=DatabaseError("no such table: listings_listingreport")):
            r = c.get("/admin/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "the database is behind the code")
