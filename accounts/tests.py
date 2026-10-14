"""
Accounts tests. Run:  python manage.py test accounts
"""
import json
import re
from io import StringIO
from unittest import mock

from django.core.cache import cache
from django.core.management import call_command
from django.test import Client, TestCase

from .models import PhoneCode, User
from .phone import normalize_phone


class PhoneTests(TestCase):
    def test_all_ways_of_writing_a_number(self):
        for raw in ["0771234567", "771234567", "263771234567", "+263 77 123 4567", "+263-77-123-4567", "00263771234567", "(077) 123 4567"]:
            self.assertEqual(normalize_phone(raw), "+263771234567", raw)

    def test_not_a_zimbabwe_mobile(self):
        for raw in ["12345", "+27821234567", "0242123456", "", "abc"]:
            with self.assertRaises(ValueError, msg=raw):
                normalize_phone(raw)


class Api:
    """Small helper: a browser with CSRF checks ON, like the real thing."""

    def __init__(self):
        self.c = Client(enforce_csrf_checks=True)
        self.c.get("/")                                  # gets the csrftoken cookie

    def post(self, url, data=None):
        token = self.c.cookies["csrftoken"].value
        return self.c.post(url, json.dumps(data or {}), content_type="application/json", HTTP_X_CSRFTOKEN=token)

    def get(self, url):
        return self.c.get(url)


def sent_code(printed):
    """Find the 6-digit code in what the test-mode WhatsApp sender printed."""
    return re.search(r"is (\d{6})", printed).group(1)


class AuthFlowTests(TestCase):
    def setUp(self):
        cache.clear()
        self.tendai = User.objects.create_user("0771234567", "murimi2026", name="Tendai Moyo", username="Tendai",
                                               email="Tendai@Example.com", role="both")

    def test_saved_in_one_form(self):
        self.tendai.refresh_from_db()
        self.assertEqual(self.tendai.phone, "+263771234567")
        self.assertEqual(self.tendai.username, "tendai")
        self.assertEqual(self.tendai.email, "tendai@example.com")
        self.assertNotEqual(self.tendai.password, "murimi2026")          # stored as a hash

    def test_login_with_phone_username_or_email(self):
        for identifier in ["077 123 4567", "+263771234567", "tendai", "TENDAI", "tendai@example.com", "Tendai@Example.COM"]:
            api = Api()
            r = api.post("/api/auth/login/", {"identifier": identifier, "password": "murimi2026"})
            self.assertEqual(r.status_code, 200, identifier)
            self.assertEqual(api.get("/api/auth/me/").json()["user"]["name"], "Tendai Moyo")

    def test_wrong_password_and_unknown_account_get_the_same_message(self):
        api = Api()
        a = api.post("/api/auth/login/", {"identifier": "tendai", "password": "wrong-pass"}).json()["error"]
        b = api.post("/api/auth/login/", {"identifier": "nobody-here", "password": "wrong-pass"}).json()["error"]
        self.assertEqual(a, b)

    def test_five_tries_then_wait(self):
        api = Api()
        for _ in range(5):
            self.assertEqual(api.post("/api/auth/login/", {"identifier": "tendai", "password": "nope"}).status_code, 400)
        r = api.post("/api/auth/login/", {"identifier": "tendai", "password": "murimi2026"})
        self.assertEqual(r.status_code, 429)                              # even the right password must wait

    def test_successful_logins_are_not_limited(self):
        """Logging in many times with the RIGHT password (several phones) never locks you out."""
        for _ in range(8):
            r = Api().post("/api/auth/login/", {"identifier": "tendai", "password": "murimi2026"})
            self.assertEqual(r.status_code, 200)

    def test_correct_login_clears_earlier_mistakes(self):
        api = Api()
        for _ in range(4):
            api.post("/api/auth/login/", {"identifier": "tendai", "password": "nope"})
        self.assertEqual(api.post("/api/auth/login/", {"identifier": "tendai", "password": "murimi2026"}).status_code, 200)
        for _ in range(4):                                                   # a fresh 5 tries again
            self.assertEqual(api.post("/api/auth/login/", {"identifier": "tendai", "password": "nope"}).status_code, 400)

    def test_login_needs_csrf_token(self):
        browser = Client(enforce_csrf_checks=True)
        r = browser.post("/api/auth/login/", json.dumps({"identifier": "tendai", "password": "murimi2026"}), content_type="application/json")
        self.assertEqual(r.status_code, 403)

    def test_logout(self):
        api = Api()
        api.post("/api/auth/login/", {"identifier": "tendai", "password": "murimi2026"})
        api.post("/api/auth/logout/")
        self.assertIsNone(api.get("/api/auth/me/").json()["user"])

    def test_register_then_confirm_code_then_logged_in(self):
        api = Api()
        out = StringIO()
        with mock.patch("sys.stdout", out):
            r = api.post("/api/auth/register/", {"name": "Rudo Chikore", "phone": "071 234 5678", "username": "rudo_c",
                                                 "email": "rudo@example.com", "password": "harvest-2026", "role": "buyer"})
        self.assertEqual(r.status_code, 201)
        user = User.objects.get(phone="+263712345678")
        self.assertFalse(user.is_active)                                 # not until the code is confirmed
        self.assertEqual(api.post("/api/auth/login/", {"identifier": "rudo_c", "password": "harvest-2026"}).status_code, 400)
        code = sent_code(out.getvalue())
        self.assertFalse(PhoneCode.objects.filter(code_hash=code).exists())    # stored as a fingerprint only
        self.assertEqual(api.post("/api/auth/verify/", {"code": "000000" if code != "000000" else "111111"}).status_code, 400)
        r = api.post("/api/auth/verify/", {"code": code})
        self.assertEqual(r.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertIsNotNone(user.phone_verified_at)
        self.assertEqual(api.get("/api/auth/me/").json()["user"]["phone"], "+263712345678")

    def test_register_errors_per_field(self):
        r = Api().post("/api/auth/register/", {"name": "", "phone": "12", "username": "a!", "email": "not-an-email",
                                               "password": "12345678", "role": "king"})
        errors = r.json()["errors"]
        for field in ["name", "phone", "username", "email", "password", "role"]:
            self.assertIn(field, errors)

    def test_cant_register_a_taken_number_username_or_email(self):
        r = Api().post("/api/auth/register/", {"name": "X Y", "phone": "0771234567", "username": "TENDAI",
                                               "email": "tendai@example.com", "password": "harvest-2026", "role": "buyer"})
        self.assertEqual(set(r.json()["errors"]), {"phone", "username", "email"})

    def test_forgot_password_same_answer_for_unknown_numbers(self):
        out = StringIO()
        with mock.patch("sys.stdout", out):
            known = Api().post("/api/auth/forgot/", {"phone": "0771234567"})
            unknown = Api().post("/api/auth/forgot/", {"phone": "0779999999"})
        self.assertEqual(known.status_code, unknown.status_code)
        self.assertEqual(set(known.json()), set(unknown.json()))
        self.assertEqual(out.getvalue().count("[WhatsApp test mode]"), 1)    # only the real account gets a message

    def test_reset_password(self):
        api = Api()
        out = StringIO()
        with mock.patch("sys.stdout", out):
            api.post("/api/auth/forgot/", {"phone": "0771234567"})
        self.assertEqual(api.post("/api/auth/password/", {"password": "new-harvest-77"}).status_code, 400)  # code first
        self.assertEqual(api.post("/api/auth/verify/", {"code": sent_code(out.getvalue())}).json()["next"], "new_password")
        self.assertEqual(api.post("/api/auth/password/", {"password": "new-harvest-77"}).status_code, 200)
        self.assertEqual(Api().post("/api/auth/login/", {"identifier": "tendai", "password": "new-harvest-77"}).status_code, 200)

    def test_one_code_a_minute(self):
        api = Api()
        with mock.patch("sys.stdout", StringIO()):
            api.post("/api/auth/forgot/", {"phone": "0771234567"})
            r = api.post("/api/auth/resend/")
        self.assertEqual(r.status_code, 429)

    def test_codes_stop_working_after_five_wrong_tries(self):
        api = Api()
        out = StringIO()
        with mock.patch("sys.stdout", out):
            api.post("/api/auth/forgot/", {"phone": "0771234567"})
        code = sent_code(out.getvalue())
        wrong = "000000" if code != "000000" else "111111"
        for _ in range(5):
            api.post("/api/auth/verify/", {"code": wrong})
        self.assertEqual(api.post("/api/auth/verify/", {"code": code}).status_code, 400)

    def test_blocked_user_cant_log_in(self):
        self.tendai.is_active = False
        self.tendai.save()
        self.assertEqual(Api().post("/api/auth/login/", {"identifier": "tendai", "password": "murimi2026"}).status_code, 400)


class SeedTests(TestCase):
    def test_seed_demo_creates_tendai_first_and_is_safe_to_repeat(self):
        call_command("seed_demo", stdout=StringIO())
        call_command("seed_demo", stdout=StringIO())
        tendai = User.objects.get(username="tendai")
        self.assertTrue(tendai.check_password("murimi2026"))
        self.assertTrue(tendai.is_verified_farmer)
        self.assertEqual(User.objects.filter(is_superuser=True).count(), 1)
