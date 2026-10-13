from django.test import TestCase


class MarketplacePageTests(TestCase):
    def test_home_page_loads(self):
        """GET / answers 200 and uses our template, not Django's rocket page."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "web/index.html")
        self.assertContains(response, "Murimi Market")

    def test_home_page_sets_csrf_cookie(self):
        """The page hands the browser a CSRF cookie for later API calls."""
        response = self.client.get("/")
        self.assertIn("csrftoken", response.cookies)

    def test_page_files_are_linked(self):
        """The page links its CSS and JavaScript from /static/web/."""
        response = self.client.get("/")
        for name in ("app.css", "mock.js", "api.js", "app.js"):
            self.assertContains(response, f"/static/web/{name}")
