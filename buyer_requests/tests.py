"""
Buyer request tests. Run:  python manage.py test buyer_requests
"""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from orders.tests import JsonBrowser, people

from .models import BuyerRequest


def form(**kw):
    data = dict(crop="Tomatoes", quantity=100, unit="crate", province="Harare", district="Avondale",
                needed_by=(timezone.localdate() + timedelta(days=5)).isoformat(), repeat="weekly",
                max_price="6.80", delivery="delivery", note="Grade A")
    data.update(kw)
    return data


class RequestTests(TestCase):
    def setUp(self):
        self.farmer, self.buyer, self.buyer2 = people()
        self.farmer2 = User.objects.create_user("+263775555555", "pw", name="Rutendo Banda", role="farmer")
        self.bb, self.fb = JsonBrowser(self.buyer2), JsonBrowser(self.farmer)

    def post_request(self, **kw):
        r = self.bb.post("/api/requests/", form(**kw))
        self.assertEqual(r.status_code, 201, r.content)
        return r.json()

    def test_post_and_list(self):
        req = self.post_request()
        self.assertEqual(req["buyer"], {"name": "FreshMart", "kind": "Supermarket"})
        self.assertEqual(req["still_needed"], 100)
        self.assertTrue(req["is_mine"])
        listed = JsonBrowser().get("/api/requests/").json()["results"]
        self.assertEqual(len(listed), 1)
        self.assertFalse(listed[0]["is_mine"])
        self.assertNotIn("263713333333", JsonBrowser().get("/api/requests/").content.decode())

    def test_form_checks(self):
        today = timezone.localdate()
        bad = [dict(crop="Gold"), dict(unit="bird"), dict(quantity=0), dict(province="Paris"),
               dict(needed_by=today.isoformat()), dict(needed_by=(today + timedelta(days=91)).isoformat()),
               dict(repeat="daily"), dict(max_price="-1"), dict(delivery="drone"), dict(note="x" * 301)]
        for change in bad:
            r = self.bb.post("/api/requests/", form(**change))
            self.assertEqual(r.status_code, 400, change)
            self.assertTrue(r.json()["errors"], change)

    def test_farmer_only_cannot_post_and_buyer_cannot_supply(self):
        self.assertEqual(self.fb.post("/api/requests/", form()).status_code, 403)
        req = self.post_request()
        r = JsonBrowser(self.buyer).post(f"/api/requests/{req['id']}/supply/", {"quantity": 1, "price": "6", "ready_on": timezone.localdate().isoformat()})
        self.assertEqual(r.status_code, 403)

    def test_supply_part_then_buyer_accepts_and_fill_grows(self):
        req = self.post_request()
        today = timezone.localdate().isoformat()
        r = self.fb.post(f"/api/requests/{req['id']}/supply/", {"quantity": 60, "price": "6.50", "ready_on": today})
        self.assertEqual(r.status_code, 201, r.content)
        o = r.json()
        self.assertEqual((o["proposed_by"], o["i_sent"], o["can"]), ("farmer", True, ["cancel"]))
        self.assertEqual(self.bb.get("/api/me/requests/").json()["results"][0]["offers_waiting"], 1)
        # The BUYER answers a supply offer
        self.assertEqual(self.fb.post(f"/api/orders/{o['id']}/accept/").status_code, 403)
        self.assertEqual(self.bb.post(f"/api/orders/{o['id']}/accept/").status_code, 200)
        listed = JsonBrowser().get("/api/requests/").json()["results"][0]
        self.assertEqual((listed["filled"], listed["suppliers"], listed["still_needed"]), (60, 1, 40))
        # Too much for what's left
        r = JsonBrowser(self.farmer2).post(f"/api/requests/{req['id']}/supply/", {"quantity": 50, "price": "6", "ready_on": today})
        self.assertEqual(r.json()["errors"]["quantity"], "They only need 40 more.")

    def test_accept_refuses_when_already_filled(self):
        req = self.post_request(quantity=50)
        today = timezone.localdate().isoformat()
        a = self.fb.post(f"/api/requests/{req['id']}/supply/", {"quantity": 40, "price": "6", "ready_on": today}).json()["id"]
        b = JsonBrowser(self.farmer2).post(f"/api/requests/{req['id']}/supply/", {"quantity": 30, "price": "6", "ready_on": today}).json()["id"]
        self.assertEqual(self.bb.post(f"/api/orders/{a}/accept/").status_code, 200)
        r = self.bb.post(f"/api/orders/{b}/accept/")
        self.assertEqual(r.status_code, 409)
        self.assertIn("Only 10 still needed", r.json()["error"])

    def test_supply_checks(self):
        req = self.post_request()
        today = timezone.localdate()
        bad = [{"quantity": 0, "price": "6", "ready_on": today.isoformat()},
               {"quantity": 1, "price": "0", "ready_on": today.isoformat()},
               {"quantity": 1, "price": "6", "ready_on": (today - timedelta(days=1)).isoformat()},
               {"quantity": 1, "price": "6", "ready_on": (today + timedelta(days=15)).isoformat()}]
        for data in bad:
            self.assertEqual(self.fb.post(f"/api/requests/{req['id']}/supply/", data).status_code, 400, data)

    def test_close_only_by_owner_then_hidden_and_no_supply(self):
        req = self.post_request()
        self.assertEqual(JsonBrowser(self.buyer).post(f"/api/requests/{req['id']}/close/").status_code, 403)
        self.assertEqual(self.bb.post(f"/api/requests/{req['id']}/close/").json()["status"], "closed")
        self.assertEqual(JsonBrowser().get("/api/requests/").json()["results"], [])
        r = self.fb.post(f"/api/requests/{req['id']}/supply/", {"quantity": 1, "price": "6", "ready_on": timezone.localdate().isoformat()})
        self.assertEqual(r.status_code, 404)
        self.assertEqual(BuyerRequest.objects.get().status, "closed")

    def test_cannot_supply_own_request(self):
        both = User.objects.create_user("+263776666666", "pw", name="Both Ways", role="both")
        b = JsonBrowser(both)
        req = b.post("/api/requests/", form()).json()
        r = b.post(f"/api/requests/{req['id']}/supply/", {"quantity": 1, "price": "6", "ready_on": timezone.localdate().isoformat()})
        self.assertEqual(r.status_code, 400)
