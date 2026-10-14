"""
Tests for /api/health/ and the JSON answer shape.

Each test is one fact we want to stay true. Run them with:
    python manage.py test core
"""
from unittest import mock

from django.db import DatabaseError
from django.test import TestCase


class HealthTests(TestCase):
    def test_health_ok(self):
        """GET /api/health/ answers 200 with JSON saying the database works."""
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["database"], "ok")
        self.assertIn("server_time", data)

    def test_health_runs_one_sql_query(self):
        """The check costs the database exactly one query (SELECT 1), no more."""
        with self.assertNumQueries(1):
            self.client.get("/api/health/")

    def test_post_is_refused_in_our_json_shape(self):
        """POST isn't allowed here: 405, an Allow header, and {"error", "errors"}."""
        response = self.client.post("/api/health/")
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response["Allow"], "GET")
        self.assertEqual(set(response.json()), {"error", "errors"})

    def test_database_down_gives_503(self):
        """If the database can't be reached, we say so (503) instead of crashing (500)."""
        with mock.patch("core.api.connection.cursor", side_effect=DatabaseError("down")):
            with self.assertLogs("core.api", level="ERROR"):
                response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["database"], "unreachable")


class CsrfTests(TestCase):
    def test_post_without_csrf_token_is_refused_in_json(self):
        """With CSRF checking ON (like a real browser), a POST with no token is stopped
        by middleware before our view: 403, in our JSON shape."""
        from django.test import Client
        browser = Client(enforce_csrf_checks=True)
        response = browser.post("/api/health/")
        self.assertEqual(response.status_code, 403)
        self.assertIn("session has expired", response.json()["error"])

    def test_post_with_csrf_token_reaches_our_view(self):
        """With a valid token, the request gets past middleware, and our @allow("GET") answers 405."""
        from django.test import Client
        browser = Client(enforce_csrf_checks=True)
        browser.get("/")                                   # the page sets the csrftoken cookie
        token = browser.cookies["csrftoken"].value
        response = browser.post("/api/health/", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 405)


class ApiNotFoundTests(TestCase):
    def test_unknown_api_address_is_json_404(self):
        response = self.client.get("/api/does-not-exist/")
        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.json())

    def test_pages_outside_api_are_not_affected(self):
        """The catch-all only covers /api/: the market page still loads."""
        self.assertEqual(self.client.get("/").status_code, 200)
