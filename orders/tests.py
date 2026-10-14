"""
Offers, orders and ratings tests. Run:  python manage.py test orders
"""
import json
from datetime import timedelta

from django.test import Client, TestCase
from django.utils import timezone

from accounts.models import User
from listings.tests import make_listing

from .models import Order, Rating


class JsonBrowser:
    """A browser with CSRF checks ON that sends JSON, like api.js does."""

    def __init__(self, user=None):
        self.c = Client(enforce_csrf_checks=True)
        self.c.get("/")
        if user:
            self.c.force_login(user)

    def post(self, url, data=None):
        return self.c.post(url, json.dumps(data or {}), content_type="application/json",
                           HTTP_X_CSRFTOKEN=self.c.cookies["csrftoken"].value)

    def get(self, url):
        return self.c.get(url)


def people():
    farmer = User.objects.create_user("+263771111111", "pw-123456", name="Tendai Moyo", role="farmer")
    buyer = User.objects.create_user("+263712222222", "pw-123456", name="Rudo Chari", role="buyer")
    buyer2 = User.objects.create_user("+263713333333", "pw-123456", name="FreshMart", role="buyer", business_type="Supermarket")
    return farmer, buyer, buyer2


class SendOfferTests(TestCase):
    def setUp(self):
        self.farmer, self.buyer, self.buyer2 = people()
        self.listing = make_listing(self.farmer, quantity=50, quantity_left=50, delivery="pickup")

    def test_buyer_sends_offer_price_is_copied_from_listing(self):
        r = JsonBrowser(self.buyer).post(f"/api/listings/{self.listing.id}/offers/",
                                         {"quantity": 10, "delivery": "pickup", "message": "Friday?", "price_usd": "0.01"})
        self.assertEqual(r.status_code, 201, r.content)
        body = r.json()
        self.assertEqual(body["price_usd"], 6.5)                 # the browser can't choose the price
        self.assertEqual(body["status"], "pending")
        self.assertEqual(body["can"], ["cancel"])
        self.assertIsNone(body["other_party"]["phone"])           # no number until accepted
        self.assertEqual(body["other_party"]["name"], "Tendai M.")

    def test_must_log_in(self):
        r = JsonBrowser().post(f"/api/listings/{self.listing.id}/offers/", {"quantity": 1, "delivery": "pickup"})
        self.assertEqual(r.status_code, 401)

    def test_csrf_is_required(self):
        c = Client(enforce_csrf_checks=True)
        c.force_login(self.buyer)
        r = c.post(f"/api/listings/{self.listing.id}/offers/", "{}", content_type="application/json")
        self.assertEqual(r.status_code, 403)
        self.assertIn("error", r.json())

    def test_farmer_only_account_cannot_buy(self):
        other = User.objects.create_user("+263774444444", "pw", name="Other Farmer", role="farmer")
        r = JsonBrowser(other).post(f"/api/listings/{self.listing.id}/offers/", {"quantity": 1, "delivery": "pickup"})
        self.assertEqual(r.status_code, 403)

    def test_own_listing(self):
        self.farmer.role = "both"
        self.farmer.save()
        r = JsonBrowser(self.farmer).post(f"/api/listings/{self.listing.id}/offers/", {"quantity": 1, "delivery": "pickup"})
        self.assertEqual(r.status_code, 400)

    def test_bad_quantity_and_delivery(self):
        b = JsonBrowser(self.buyer)
        for qty in (0, -1, 51, "abc"):
            r = b.post(f"/api/listings/{self.listing.id}/offers/", {"quantity": qty, "delivery": "pickup"})
            self.assertEqual(r.status_code, 400)
            self.assertIn("quantity", r.json()["errors"])
        r = b.post(f"/api/listings/{self.listing.id}/offers/", {"quantity": 1, "delivery": "delivery"})
        self.assertEqual(r.json()["errors"]["delivery"], "This farmer only offers collection.")

    def test_one_waiting_offer_per_listing(self):
        b = JsonBrowser(self.buyer)
        self.assertEqual(b.post(f"/api/listings/{self.listing.id}/offers/", {"quantity": 1, "delivery": "pickup"}).status_code, 201)
        self.assertEqual(b.post(f"/api/listings/{self.listing.id}/offers/", {"quantity": 1, "delivery": "pickup"}).status_code, 409)

    def test_closed_listings_refuse_offers(self):
        for change in ({"status": "sold_out"}, {"status": "draft"}, {"quantity_left": 0},
                       {"available_from": timezone.localdate() + timedelta(days=30)}):
            l = make_listing(self.farmer, **change)
            r = JsonBrowser(self.buyer).post(f"/api/listings/{l.id}/offers/", {"quantity": 1, "delivery": "pickup"})
            self.assertEqual(r.status_code, 404, change)


class ActionTests(TestCase):
    def setUp(self):
        self.farmer, self.buyer, self.buyer2 = people()
        self.listing = make_listing(self.farmer, quantity=50, quantity_left=50)
        self.fb, self.bb = JsonBrowser(self.farmer), JsonBrowser(self.buyer)

    def offer(self, browser=None, qty=10):
        r = (browser or self.bb).post(f"/api/listings/{self.listing.id}/offers/", {"quantity": qty, "delivery": "pickup"})
        self.assertEqual(r.status_code, 201, r.content)
        return r.json()["id"]

    def test_accept_lowers_stock_and_reveals_numbers(self):
        oid = self.offer()
        r = self.fb.post(f"/api/orders/{oid}/accept/")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["other_party"]["phone"], "+263712222222")
        self.assertEqual(r.json()["other_party"]["name"], "Rudo Chari")
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.quantity_left, 40)
        mine = self.bb.get("/api/me/orders/").json()["results"][0]
        self.assertEqual(mine["other_party"]["phone"], "+263771111111")
        self.assertEqual(mine["can"], ["complete"])

    def test_only_receiver_answers_only_sender_cancels(self):
        oid = self.offer()
        self.assertEqual(self.bb.post(f"/api/orders/{oid}/accept/").status_code, 403)
        self.assertEqual(self.fb.post(f"/api/orders/{oid}/cancel/").status_code, 403)
        stranger = JsonBrowser(self.buyer2)
        self.assertEqual(stranger.post(f"/api/orders/{oid}/decline/").status_code, 404)
        self.assertEqual(self.bb.post(f"/api/orders/{oid}/cancel/").json()["status"], "cancelled")
        self.assertEqual(self.fb.post(f"/api/orders/{oid}/accept/").status_code, 409)   # already cancelled

    def test_cannot_accept_more_than_is_left(self):
        a = self.offer(qty=40)
        b = self.offer(JsonBrowser(self.buyer2), qty=20)
        self.assertEqual(self.fb.post(f"/api/orders/{a}/accept/").status_code, 200)
        r = self.fb.post(f"/api/orders/{b}/accept/")
        self.assertEqual(r.status_code, 409)
        self.assertIn("Only 10 crates left", r.json()["error"])
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.quantity_left, 10)

    def test_accept_twice_does_not_sell_twice(self):
        oid = self.offer()
        self.assertEqual(self.fb.post(f"/api/orders/{oid}/accept/").status_code, 200)
        self.assertEqual(self.fb.post(f"/api/orders/{oid}/accept/").status_code, 409)
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.quantity_left, 40)

    def test_unknown_action(self):
        oid = self.offer()
        self.assertEqual(self.fb.post(f"/api/orders/{oid}/explode/").status_code, 404)

    def test_complete_then_rate_once_each(self):
        oid = self.offer()
        self.fb.post(f"/api/orders/{oid}/accept/")
        self.assertEqual(self.bb.post(f"/api/orders/{oid}/rating/", {"stars": 5}).status_code, 409)   # not completed yet
        self.assertEqual(self.bb.post(f"/api/orders/{oid}/complete/").json()["can"], ["rate"])
        self.assertEqual(self.bb.post(f"/api/orders/{oid}/rating/", {"stars": 9}).status_code, 400)
        r = self.bb.post(f"/api/orders/{oid}/rating/", {"stars": 4, "comment": "Good crates"})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["my_rating"], {"stars": 4, "comment": "Good crates"})
        self.assertEqual(r.json()["can"], [])
        self.assertEqual(self.bb.post(f"/api/orders/{oid}/rating/", {"stars": 5}).status_code, 409)
        self.assertEqual(self.fb.post(f"/api/orders/{oid}/rating/", {"stars": 5}).status_code, 201)
        self.assertEqual(Rating.objects.count(), 2)
        # The farmer's card now shows the record
        card = JsonBrowser().get("/api/listings/").json()["results"][0]["farmer"]
        self.assertEqual((card["rating"], card["completed_orders"]), (4.0, 1))
        detail = JsonBrowser().get(f"/api/listings/{self.listing.id}/").json()["farmer"]
        self.assertEqual(detail["reviews"][0]["comment"], "Good crates")
        self.assertEqual(detail["reviews"][0]["by"], "Rudo C.")

    def test_lists_show_only_my_side(self):
        self.offer()
        self.assertEqual(len(self.fb.get("/api/me/offers/").json()["results"]), 1)
        self.assertEqual(len(self.fb.get("/api/me/orders/").json()["results"]), 0)
        self.assertEqual(len(JsonBrowser(self.buyer2).get("/api/me/orders/").json()["results"]), 0)
        self.assertEqual(JsonBrowser().get("/api/me/offers/").status_code, 401)

    def test_pending_offers_count_on_my_listings(self):
        self.offer()
        self.offer(JsonBrowser(self.buyer2))
        mine = self.fb.get("/api/me/listings/").json()["results"][0]
        self.assertEqual(mine["pending_offers"], 2)

    def test_database_refuses_order_with_yourself(self):
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Order.objects.create(listing=self.listing, farmer=self.farmer, buyer=self.farmer, crop="Tomatoes",
                                 unit="crate", price_usd=1, quantity=1, delivery="pickup")


class LimitTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.farmer, self.buyer, self.buyer2 = people()
        self.listing = make_listing(self.farmer, quantity=500, quantity_left=500)

    def test_offer_flood_is_stopped(self):
        b = JsonBrowser(self.buyer)
        codes = [b.post(f"/api/listings/{make_listing(self.farmer).id}/offers/", {"quantity": 1, "delivery": "pickup"}).status_code
                 for _ in range(32)]
        self.assertEqual(codes[:30], [201] * 30)
        self.assertEqual(codes[30:], [429, 429])

    def test_request_flood_is_stopped(self):
        from buyer_requests.tests import form
        b = JsonBrowser(self.buyer2)
        codes = [b.post("/api/requests/", form()).status_code for _ in range(12)]
        self.assertEqual(codes[:10], [201] * 10)
        self.assertEqual(codes[10:], [429, 429])
