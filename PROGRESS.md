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

**Next:** Lesson 3: the first real JSON endpoint (`/api/health/`), then Users. After that, swap `api.js` functions to real `fetch()` calls one by one.
