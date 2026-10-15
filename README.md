# Murimi Market

A marketplace where Zimbabwean farmers sell produce directly to buyers, at a fair price.
Part of the Murimi Intelligent Hub.

Farmers list what they have (or what will be ready within two weeks), buyers browse by
product and province, and the two sides agree a deal. Buyers can also post what they
need, and several farmers can each supply part of it. Nobody's phone number is shown
until an offer is accepted.

Built with Django 5.2 and plain HTML, CSS and JavaScript. No front-end framework.

---

## Run it on this laptop

Double-click **`start-windows.bat`**, or in PowerShell:

```powershell
cd C:\murimi-market
.\start-windows.bat
```

That makes the private Python folder (`.venv`), installs what's needed, creates a `.env`
with a fresh secret key, sets up the database, adds sample data, and starts the server at
**http://127.0.0.1:8000**.

Leave that window open: WhatsApp confirmation codes are printed in it while the site is
in test mode.

### Sample accounts

| Who | Log in with | Password |
|---|---|---|
| Tendai Moyo (sells and buys) | `tendai` or 077 123 4567 | `murimi2026` |
| Rudo (buyer) | `rudo` or 071 234 5678 | `murimi2026` |
| Staff, for `/admin/` | 078 000 0000 | `murimi-staff-2026` |

These exist only after `seed_demo` runs, which `start-windows.bat` does.
**Never run the seed commands on a real server, and change these passwords before
going live.** See `docs/going-live.md`.

### Tests

```powershell
.\.venv\Scripts\python.exe manage.py test
```

122 tests covering accounts, listings, prices, offers and orders, buyer requests,
staff tools, security and the pages.

---

## How the code is laid out

One Django app per job, each with its own models, JSON endpoints, admin and tests:

| Folder | What it does |
|---|---|
| `accounts` | People: phone/username/email log-in, WhatsApp codes, roles, verification |
| `listings` | Produce for sale, photos, and staff reports about a listing |
| `prices` | Market prices (Mbare and others) behind the fair-price meter |
| `orders` | Offers, orders and star ratings |
| `buyer_requests` | "I need 300 crates of tomatoes every week" |
| `core` | Shared JSON helpers, the health check, security headers, staff home page |
| `web` | The pages themselves, and all the CSS and JavaScript |
| `config` | Settings and the main address list |

The browser talks to the server only through `/api/...`, and only through one file,
`web/static/web/api.js`. Every answer has the same shape, and every error looks like
`{"error": "...", "errors": {"field": "..."}}`.

### Some decisions worth knowing

- **Phone numbers are the log-in name**, stored as `+2637XXXXXXXX` however they're typed.
- **Prices are copied onto an offer** when it is sent, so a later price change never
  changes a deal that was already agreed.
- **Accepting an offer locks the row** in the database, so the same last crate can never
  be sold twice.
- **Photos are re-saved by the server** as JPEGs of at most 1600px, which also strips the
  GPS location a phone camera adds.
- **Nothing is trusted from the browser.** Every rule is checked again on the server.
- **The app never touches anyone's money.** People arrange payment themselves.

---

## Other reading

- **`PROGRESS.md`** — what was built, in order, and why. Start here.
- **`docs/going-live.md`** — what hosting, a domain and WhatsApp cost, and the order to
  do things.

## Not in this repository

`.env` (secrets), `db.sqlite3` (the database), `media/` (uploaded photos), `.venv/` and
`backups/` are all deliberately left out. `start-windows.bat` recreates everything you
need.
