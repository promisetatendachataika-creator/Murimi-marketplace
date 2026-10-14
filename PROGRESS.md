# Murimi Marketplace: Progress log

Paste this file into a new chat to continue where we left off.

## Lesson 1: Setup (done 13 Oct 2026)

**Finished**
- `C:\murimi-market` Django 5.2 project, settings package named `config`.
- `.venv`, `requirements.txt` (Django 5.2.x only).
- Settings read secrets from `.env`; `.env.example` is the template; PostgreSQL switch via `POSTGRES_*` (same as the Hub). Time zone Africa/Harare.
- `start-windows.bat`: makes `.venv`, installs packages, creates `.env` with a fresh secret key (first run only), migrates, runs at http://127.0.0.1:8000.
- `.gitignore` (keeps `.env`, `.venv`, `db.sqlite3`, uploads out of git). First git commit.

**Learned**
- Path of a request: browser → runserver → middleware → `config/urls.py` → view → response.
- `migrate` turns migration files into real SQL tables (`django_session`, `auth_user`, ...).
- `db.sqlite3` is data, not code, so it is not committed.

**Important note for Lesson 3**
- The current `db.sqlite3` contains Django's default `auth_user` table. Before we create our own phone-based User, we delete `db.sqlite3` and migrate again (safe: it holds no real data).

## Lesson 2 (changed at Promise's request): Front end first (done 13 Oct 2026)

**Finished**
- New app `web`: `views.index` serves `web/templates/web/index.html` at `/`, with the CSRF cookie set for later API calls.
- Page files in `web/static/web/`: `app.css` (brand look, light + dark), `mock.js` (sample data), `api.js` (the "waiter": the only file that will change when the real API exists), `app.js` (draws the page).
- Hero with the split MURIMI word and a Zimbabwe map with province pins (counts are clickable filters).
- Browse with crop chips, province, max price, sort, "sell today"; listing cards with the fair-price meter, verified badge, ratings, harvest date.
- Offer sheet (quantity check, total, pickup or delivery), Sell sheet with a live price check, buyer requests with "how much is filled" bars, How it works tabs, WhatsApp footer.
- 3 tests in `web/tests.py`.

**Learned**
- URL `/` → `config/urls.py` → `web/urls.py` → `web/views.py:index()` → template → HTML; the browser then fetches CSS/JS from `/static/`.
- The page only talks to `MarketAPI`; today it answers from mock data, later from `/api/...`.

**Note:** the map image came from Promise. Confirm we may use it publicly before going live.

## Front-end tweaks (14 Oct 2026)
- All emojis removed; close, verified tick and rating star are now small SVG icons.
- Listing cards, the offer sheet and buyer requests use real crop photos (`web/static/web/img/crops/*.webp`, 9 to 44 KB each, lazy-loaded).
- Cards say "Example photo" until farmers upload their own (Lesson 7: `photo_url` replaces it automatically).
- Maize and Sugar beans photos added (14 Oct). Every crop now has a photo.
- Before going live: the maize photo has a stock-site watermark, so replace it with our own or a licensed photo.
- Tobacco and Cotton are back in the crop chips, with one sample listing each.
- Tests: 5 (added "crop photos exist" and "no emoji on the page").

## Coming soon + poultry (14 Oct 2026)
- **Coming soon listings:** a farmer can list produce that will be ready within 14 days (`READY_WINDOW_DAYS`). Cards show "Coming soon: 2 weeks away" (weeks rounded up; 1 to 3 days shown in days), the Ready line shows the date and days, the button says "Reserve for <date>", and the offer sheet becomes a reservation. Filter "When": Any time / Ready now / Coming soon.
- Rule (checked in api.js now, and on the server later): `available_from` must be between today and today + 14 days. Listings further away are hidden and refused.
- **Poultry:** new `POULTRY = ["Broilers", "Eggs"]` list next to the Hub's CROPS. The Hub's choices.py must get the same list when we link the two.
- New units: `bird` and `tray_30` (tray of 30 eggs). Each product only offers units that fit (`PRODUCT_UNITS`): broilers per bird or kg, eggs per tray.
- Card wording: eggs say "Collected", broilers "Ready since", crops "Harvested".
- Sample market prices for broilers and eggs (made up, for the demo).
- Tests: 5, now checking 11 product photos.
- **For the database lesson:** a listing needs `available_from` (date) and the server works out `ready_in_days`; no extra status is needed.

## Log-in page (14 Oct 2026)
- New page in the style Promise chose: white card, form on the left, cut-paper waves over leaves on the right. On phones the leaves fill the screen behind a frosted-glass card.
- URLs: `/login/`, `/register/`, `/forgot/` -> `web/views.py:account_page()` -> `web/templates/web/login.html`. `?next=` only allows our own pages (stops "open redirect" tricks).
- Files: `web/static/web/auth.js` (the forms), `auth.css` (the look), `img/leaves.webp` (35 KB).
- Flows (demo data in api.js, same JSON shape as the future server):
  - Log in with WhatsApp number (any format: 0771234567, +263 77...) or username. Demo account: 077 123 4567 or `tendai`, password `murimi2026`.
  - Create account: Sell / Buy / Both, name, WhatsApp number, optional username, password -> 6-digit WhatsApp code (demo code 123456) -> logged in.
  - Forgot password: number -> code -> new password.
- Security habits already in the page: same error for wrong number or wrong password; 5 tries then "wait 15 minutes"; "forgot" answers the same whether or not the number has an account; password needs 8+ characters and not only numbers.
- Main page: "Log in" now links to /login/; when logged in the top bar shows "Hi, Name" and Log out.
- No Google or Microsoft log-in buttons: our accounts are WhatsApp numbers, like the Hub.
- Tests: 8.

## Bug fix: map pins and province list disappeared (14 Oct 2026)
- **Symptom:** no pins on the map, Province list only "All provinces".
- **Cause (reproduced):** the browser kept an OLD saved copy of `api.js` while loading the NEW `app.js`. The new app.js called `MarketAPI.me()` and `meta.products`, which the old file doesn't have, so start-up stopped before the menus and pins were built.
- **Fix 1, cache busting:** new template tag `{% asset 'web/app.js' %}` (`web/templatetags/asset_tags.py`) adds `?v=<time the file changed>` to every CSS/JS address, so a changed file always gets fetched fresh.
- **Fix 2, sturdier start-up:** `app.js start()` runs each part in `step()`. If one part fails, the rest still works and the error appears in the browser console (F12) as `[Murimi] ... failed`.
- **Lesson:** after a new Python file (like a template tag), restart the server.

## My account page (14 Oct 2026)
- New page `/account/` -> `views.my_account()` -> `account.html` + `account.js` + `account.css`. Logged-out visitors go to `/login/?next=/account/`.
- Tabs by role: farmers see **Offers on my produce** and **My listings**; buyers see **My orders**; "both" sees all three. The demo account Tendai is now "both".
- Offers are grouped: Waiting for your answer / Accepted / Finished, each with a Sent -> Accepted -> Completed track.
- **Status rules** (`TRANSITIONS` in api.js, the server will copy it): accept and decline = farmer, only from pending; cancel = buyer, only from pending; complete = either side, only from accepted. Anything else is refused (403 or 409).
- **Accept lowers the quantity left**, and refuses if not enough is left ("Only 64 left, but this offer asks for 70"). Server version: `transaction.atomic()` + `select_for_update()`.
- **Contact reveal:** the other side's WhatsApp number is only sent by the API after "accepted", with an Open WhatsApp button and a ready-written message.
- **Ratings:** after "completed", each side rates the other once (1 to 5 stars and a comment).
- My listings: on the market / coming soon / draft / sold out, quantity left, sold so far, offers waiting, Mark sold out. Edit is a placeholder for now.
- Decline, cancel, complete and sold out ask "Yes, ..." once before doing it (no browser pop-ups).
- Main page: sending an offer needs log-in; offers sent from the main page appear in My account; the top bar shows "My account".
- Demo data is saved in the browser; "Put the sample offers back" resets it.
- Tidy-up for later: account.js repeats a few helpers from app.js (photos, units); move them into one shared file.
- Tests: 10.

## Listing details page (14 Oct 2026)
- New page `/listing/<id>/` (e.g. `/listing/101/`) -> `views.listing_page()` -> `listing.html` + `listing.js` + `listing.css`. `<int:listing_id>` in urls.py means `/listing/abc/` is a 404 before our code runs.
- Each listing has its own address, so it can be shared on WhatsApp ("Share on WhatsApp" and "Copy link" buttons). The browser tab title shows crop, variety and price.
- Shows: photo gallery (farmer's photos, or one example photo clearly labelled), price, fair-price meter **with a plain explanation**, the farmer's description, facts (available, harvested or ready, grade, where, getting it, listed), offer form (or reservation for coming soon), farmer profile (member since, Murimi Verified explained or a safety warning if not verified, completed orders, average rating, reviews), more from this farmer, other listings of the same crop.
- Phones: price and "Make an offer" stay fixed at the bottom of the screen.
- Your own listing shows "This is your listing" instead of the offer form; sold out shows "Sold out"; missing listings show a friendly "We can't find that listing".
- API: `MarketAPI.getListing(id)` (later `GET /api/listings/<id>/`). It never includes the farmer's phone number, and hides drafts from everyone except the owner.
- Main page: card photos and titles now open the listing page.
- New shared helpers file `common.js` (used by the listing page; app.js and account.js move onto it later).
- Sample farmer photos for listing 101 in `img/sample/`.
- Tests: 13.

## Complete Sell form (14 Oct 2026)
- The Sell form now has 6 labelled parts: What (product, variety, quantity, unit), Price (US$, optional ZiG, live market check), When (ready now + harvested/collected date, or ready within 2 weeks + ready date; must sell today), Where (province, district, and how buyers get it: collect / I deliver / both), Photos (up to 3), Description (up to 500 characters with a counter).
- **Save as draft** (can be half-finished, only the farmer sees it in My account) or **Publish listing** (everything required).
- **Photos are shrunk in the browser** before sending: max 1280 px, JPEG 72%. A 1.3 MB phone photo became about 120 KB. Only JPG, PNG and WebP up to 10 MB are accepted; the server will check the file bytes again (same rule as the Hub's documents app).
- Selling needs log-in: logged-out farmers go to `/login/?next=/#sell` and the form opens when they come back. Buyer-only accounts are told selling needs a farmer account.
- `MarketAPI.createListing()` checks every field and answers with per-field errors (later `POST /api/listings/`). The farmer's name and verified badge come from their account, never from the form.
- New listings appear on the market (first in their crop), on the map counts, on their own listing page with the farmer's photos, and in My listings. Drafts only in My listings.
- ZiG prices show next to US$ on cards and the listing page when given.
- Tests: 14.

## Buyer requests: post, supply, accept (14 Oct 2026)
- **Post what you need** (buyers): product, grade, quantity, unit, needed by (tomorrow to 3 months), how often (once / every week / every 2 weeks / every month), province and area, delivery or collection, most you'll pay (optional, with today's market price shown), note.
- **Offer to supply** (farmers): all of a request **or part of it** (light pooling: several small farms fill one big order), own price, ready date (up to 14 days), grade, message.
- **One set of rules for both kinds of offer:** `TRANSITIONS` now says *receiver* accepts or declines, *sender* cancels, either completes. A normal offer: buyer sends, farmer receives. A supply offer: farmer sends, buyer receives (`proposed_by: "farmer"`). The server will store the same field.
- Accepting a supply offer adds to the request's "filled" amount and is refused if it's more than still needed.
- My account: groups are now *Waiting for your answer* / *Waiting for the other side* / *Accepted* / *Finished*; supply offers carry a label; new **My requests** tab (fill bar, offers waiting, Close request).
- Market page: requests show area, how often, delivery, the most the buyer pays, and notes; your own request shows "Your request: see offers"; empty search results offer "Post what you need".
- Titles read naturally: "10 trays of 30 eggs", "40 broilers", "20 bags of 50 kg of maize".
- Tests: 16.

## Second pass: trust and weak connections (14 Oct 2026)
- **Old market prices:** a price older than 7 days (`PRICE_FRESH_DAYS`) is not compared. Cards, the listing page, the Sell form and the request form say "Market price is out of date: the last ... was ... 12 days ago. Too old to compare."
- **Filters in the page address:** `/?crop=Maize&province=Mashonaland+West`. Refreshing keeps your search; a shared link opens the same view; Back and Forward work.
- **Share on WhatsApp** link on every card (opens WhatsApp with the crop, price, place and the listing's link).
- **Loading and no connection:** grey placeholder cards while loading; "We couldn't load the produce. Check your connection ... Try again" for listings and buyer requests. Practise with `/?demo=offline` and `/?demo=slow`.
- **Show more:** 12 listings at a time (SQL later: `LIMIT 12 OFFSET 12`), with "20 listings, showing 12" and "Show more (8 more)".
- **Honest count:** the hero says "listings open now" instead of "listings this week".
- **Must sell today** listings show "until 6 pm" (`SELL_TODAY_ENDS_HOUR`) and leave the market after 6 pm on the day they were listed.
- **My account:** one plain sentence at the top of each tab saying what it's for.
- Sample market prices now use dates relative to today, so the demo doesn't go out of date.
- **Bug found and fixed while testing:** Show more stopped at 12 with "Cannot read properties of null (reading 'stale')". The new old-price check ran before the "is there a price at all?" check, and listings with no price (tobacco, cotton) were on page 2. Fix: check the price exists first.
- Tests: 18.

## Lesson 3: first JSON endpoint `/api/health/` (14 Oct 2026)
Full notes: `docs/lessons/03-first-endpoint.md`.

**Finished**
- New app `core`: `api.py` (`health()`, JSON `not_found()`, JSON `csrf_failure()`), `http.py` (`json_error()`, `@allow()`), `urls.py`, `tests.py` (8 tests).
- `GET /api/health/` runs `SELECT 1` and answers `{"status": "ok", "database": "ok", "database_engine": "sqlite", "server_time": ..., "version": "0.1"}`; 503 if the database is down.
- Every `/api/` failure uses the Hub's shape `{"error", "errors"}`: 403 (CSRF), 404 (unknown address), 405 (wrong method, with `Allow` header).
- `api.js` made its first real `fetch()`; the main page footer shows "Server: connected. Database: sqlite".

**Learned**
- Request path: middleware → `config/urls.py` → `core/urls.py` → `@allow` → `health()` → SQL → `JsonResponse`.
- HTTP status codes 200, 400, 401, 403, 404, 405, 409, 503 and what each means.
- **Middleware runs before views:** a POST with no CSRF token never reaches our code. Found because Django's test client turns CSRF checks off; fixed with `CSRF_FAILURE_VIEW` and tests using `enforce_csrf_checks=True`.

## Project moved to C:\murimi-market (14 Oct 2026)
- Copied out of OneDrive (robocopy, without .venv); all files checked identical; tests pass there. Git now has all work committed. Claude commits after each job.

## Job 2: Accounts, real backend (14 Oct 2026)
- New app `accounts`: `choices.py` (Hub's PROVINCES and CROPS, plus POULTRY and marketplace roles), `phone.py` (`normalize_phone`: every way of writing a number becomes +2637XXXXXXXX), `models.py`, `backends.py`, `api.py`, `whatsapp.py`, `admin.py`, `seed_demo` command, 19 tests.
- **User table** (`AUTH_USER_MODEL = "accounts.User"`): phone (unique, the log-in name), username (optional, unique, lower-case), email (optional, unique, lower-case), name, role (farmer / buyer / both), phone_verified_at, is_verified_farmer + date, is_active, is_staff. Passwords are salted hashes.
- **Log in with WhatsApp number, username OR email** (`PhoneUsernameEmailBackend`).
- **PhoneCode table**: 6-digit codes stored only as HMAC fingerprints, 10 minutes, 5 wrong tries, older codes stop working when a new one is sent.
- Endpoints under `/api/auth/`: `me`, `login`, `logout`, `register`, `verify`, `resend`, `forgot`, `password`. All POSTs need the CSRF token. Errors in the `{"error", "errors"}` shape.
- Rules: only WRONG log-in tries count (5 per account, 20 per network address, 15 minutes; a correct log-in clears the count); one code a minute and 5 an hour per number; same message for wrong number/password; "forgot" gives the same answer for unknown numbers and sends nothing; new accounts stay switched off until the WhatsApp code is confirmed.
- WhatsApp **test mode** (`WHATSAPP_MODE=test`, like the Hub): codes are printed in the server window.
- Staff admin: search people, mark **Murimi Verified**, block accounts; codes visible as "sent" but never readable.
- Front end: the log-in page is now REAL (api.js `call()` sends JSON + CSRF). Register has an optional **Email** field. Other features (offers, listings, requests) still use sample data but now use the real logged-in user.
- `start-windows.bat` runs `seed_demo`: Tendai (077 123 4567 / tendai / tendai@example.com, `murimi2026`, sells and buys, Murimi Verified), Rudo (071 234 5678 / rudo, `murimi2026`, buyer), staff 078 000 0000 / `murimi-staff-2026` for /admin/ (change before going live).
- Fresh database: the old db.sqlite3 (no real data) was replaced, because the custom User must exist before the first migration.
- Bugs found by tests and fixed: a duplicate username/email wasn't flagged when the number also belonged to an active account; the log-in limit counted successful log-ins too.
- Tests: 45.

**Next:** Job 3: Listings (real table, photo uploads checked on the server, filters, Show more, drafts, sold out, coming soon).
