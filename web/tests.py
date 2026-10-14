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
        for name in ("app.css", "api.js", "app.js"):
            self.assertContains(response, f"/static/web/{name}?v=")   # version number stops stale copies

    def test_crop_photos_are_served(self):
        """Every crop photo the page asks for really exists in static files."""
        from django.contrib.staticfiles import finders
        for name in ("broilers", "eggs", "maize", "beans", "tomatoes", "potatoes", "citrus", "avocados", "tobacco", "cotton", "grain"):
            self.assertIsNotNone(finders.find(f"web/img/crops/{name}.webp"), name)

    def test_page_has_no_emoji(self):
        """Promise asked for no emojis: check the page HTML has none."""
        html = self.client.get("/").content.decode("utf-8")
        self.assertFalse([c for c in html if ord(c) >= 0x1F300], "emoji found in page")


class AccountPageTests(TestCase):
    def test_login_register_forgot_pages_load(self):
        """/login/, /register/ and /forgot/ all answer 200 with the same template."""
        for url, mode in (("/login/", "login"), ("/register/", "register"), ("/forgot/", "forgot")):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)
            self.assertTemplateUsed(response, "web/login.html")
            self.assertContains(response, f'data-mode="{mode}"')
            self.assertIn("csrftoken", response.cookies)

    def test_next_must_stay_on_our_site(self):
        """?next= may only point inside Murimi, never to another website."""
        self.assertContains(self.client.get("/login/?next=/sell/"), 'data-next="/sell/"')
        for bad in ("https://evil.example", "//evil.example"):
            self.assertContains(self.client.get("/login/", {"next": bad}), 'data-next="/"')

    def test_main_page_links_to_login(self):
        self.assertContains(self.client.get("/"), 'href="/login/"')


class MyAccountPageTests(TestCase):
    def test_account_page_loads(self):
        response = self.client.get("/account/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "web/account.html")
        for name in ("account.css", "account.js", "api.js"):
            self.assertContains(response, f"/static/web/{name}?v=")

    def test_main_page_links_to_account(self):
        self.assertContains(self.client.get("/"), 'href="/account/"')


class ListingPageTests(TestCase):
    def test_listing_page_loads(self):
        """/listing/101/ answers 200, uses the template, and passes the id to the page."""
        response = self.client.get("/listing/101/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "web/listing.html")
        self.assertContains(response, 'data-listing="101"')
        for name in ("common.js", "listing.js", "listing.css"):
            self.assertContains(response, f"/static/web/{name}?v=")

    def test_listing_id_must_be_a_number(self):
        """<int:listing_id> in urls.py: letters never reach the view."""
        self.assertEqual(self.client.get("/listing/abc/").status_code, 404)

    def test_sample_photos_exist(self):
        from django.contrib.staticfiles import finders
        for n in (1, 2, 3):
            self.assertIsNotNone(finders.find(f"web/img/sample/listing-101-{n}.webp"))


class SellFormTests(TestCase):
    def test_sell_form_has_every_field(self):
        """The Sell form asks for everything a listing needs (spec: version 1 listings)."""
        html = self.client.get("/").content.decode()
        for name in ('name="crop"', 'name="variety"', 'name="quantity"', 'name="unit"', 'name="price"',
                     'name="price_zig"', 'name="harvested_on"', 'name="available"', 'name="province"',
                     'name="district"', 'name="delivery"', 'id="photoInput"', 'name="description"'):
            self.assertIn(name, html)
        self.assertIn('value="draft"', html)       # Save as draft
        self.assertIn('value="publish"', html)     # Publish listing


class BuyerRequestTests(TestCase):
    def test_request_and_supply_forms_on_main_page(self):
        html = self.client.get("/").content.decode()
        for bit in ('id="postRequestBtn"', 'id="requestForm"', 'name="needed_by"', 'name="repeat"', 'name="max_price"',
                    'id="supplyForm"', 'name="ready_on"'):
            self.assertIn(bit, html)

    def test_account_has_my_requests_tab(self):
        self.assertContains(self.client.get("/account/"), 'id="panel-requests"')


class SecondPassTests(TestCase):
    def test_main_page_has_load_more_and_honest_count(self):
        html = self.client.get("/").content.decode()
        self.assertIn('id="loadMore"', html)
        self.assertIn("listings open now", html)
        self.assertNotIn("listings this week", html)

    def test_filters_in_address_still_serve_the_page(self):
        """/?crop=Tomatoes&province=Harare is the same page; JavaScript reads the filters."""
        self.assertEqual(self.client.get("/", {"crop": "Tomatoes", "province": "Harare"}).status_code, 200)


class RedirectTests(TestCase):
    def test_next_only_accepts_paths_on_this_site(self):
        for bad in ["//evil.com", "/\\evil.com", "/\t/evil.com", "https://evil.com", "javascript:alert(1)", "evil.com", "/\n/evil.com"]:
            html = self.client.get("/login/", {"next": bad}).content.decode()
            self.assertIn('data-next="/"', html, bad)
        self.assertIn('data-next="/account/"', self.client.get("/login/", {"next": "/account/"}).content.decode())
