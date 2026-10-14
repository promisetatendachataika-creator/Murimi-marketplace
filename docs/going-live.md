# Going live: what it costs and the order to do it

Written 14 October 2026. Prices checked on that date and they change, so confirm
before you pay. Every figure is in US dollars per month unless it says otherwise.

**The short version.** You can put Murimi Market on the internet for farmers to try
for **nothing**. A real site that stays awake and keeps its data costs about
**$13 a month**, plus **$3 a year** for a .co.zw name. WhatsApp codes cost well
under a cent each. **You do not need a payments company**, because the app doesn't
touch anyone's money.

---

## 1. The app doesn't handle money, and that's deliberate

Today a buyer sends an offer, the farmer accepts, and then the two of them get each
other's WhatsApp number and sort out payment and delivery themselves, exactly as they
would at the market. Murimi Market introduces them and keeps the record.

That means **no payments company, no merchant account, no compliance work and no
percentage off every sale** to go live. It also means no money can go missing through
the app, which is the safest place to start.

For later, if you ever want Murimi to hold the money until the produce arrives
(an escrow), the Zimbabwean option is **Paynow**: no signup or monthly fee, and a
commission per transaction of **2.5% on EcoCash, OneMoney and Telecash**, or
**3.5% + $0.50 on Visa and Mastercard**. You need a Zimbabwean bank account, and
card payments need Verified Merchant status. Don't do this until farmers are asking
for it; it adds real legal and support work.

---

## 2. Costs at a glance

| Thing | Cheapest start | What I'd actually use | Note |
|---|---|---|---|
| Hosting | **$0** (Render free) | **$7** Render Starter | Free one sleeps after 15 minutes |
| Database | **$0** (Render free Postgres) | **$6** Render Postgres Basic | The free one is **deleted after 30 days** |
| Photo storage | **$0** | **$0** Cloudflare R2 | Free up to 10 GB, no charge for people viewing |
| Domain name | **$0** (free .onrender.com address) | **$3/year** .co.zw | .com is about $18/year |
| HTTPS padlock | **$0** | **$0** | Included by the host |
| WhatsApp codes | **$0** (test mode) | **well under 1c** per code | You pay per message sent |
| Payments | **$0** | **$0** | Not needed, see above |
| **Monthly total** | **$0** | **about $13** | |

### Other hosts I looked at

| Host | Cheapest real setup | Worth knowing |
|---|---|---|
| **Render** | $7 app + $6 database = **$13** | Easiest. Deploys from GitHub. Free tier to try. |
| **Railway** | $5/month plan, which includes $5 of use | Use is metered, so the bill moves around |
| **Fly.io** | $3.69 app, but their managed Postgres is **$38** | Only cheap if you run the database yourself |
| **PythonAnywhere** | **$10** Developer | Made for Python, simple, but their free plan can't reach the whole internet |
| **Hetzner** | **about $5** for a whole 4 GB server | Cheapest by far, but **you** become the sysadmin: updates, backups, security |
| **Heroku** | $5 Eco + $5 database | Heroku went into "sustaining engineering" in Feb 2026, so I'd avoid it for something new |

**My advice:** start free on Render to show people. Move to the $13 Render setup when
real farmers are using it. Only consider Hetzner later, when saving $8 a month is worth
a weekend of learning server admin. A server you forget to update is worse than no
saving at all.

**One thing about distance:** all these hosts are in Europe or America. A page will take
a moment longer to load in Harare than it does on your laptop. Render and Fly both have
Frankfurt regions, which are the closest of the options; pick a European region, not a
US one.

---

## 3. WhatsApp codes: what they really cost

Right now `WHATSAPP_MODE=test` prints codes in the server window. For real codes you
need a Meta WhatsApp Business account, and you pay **per message**.

Meta doesn't publish a Zimbabwe line in the rate cards I could find. The nearby rates
for an authentication message are **$0.0040** ("Rest of Africa"), **$0.0067** (Nigeria),
**$0.0095** (South Africa), and **$0.0077** for "Other". So assume roughly
**half a US cent to one cent per code**.

In plain terms: **1,000 farmers signing up costs about $5 to $10 in codes.** At that
price it isn't what will stop you.

Things to know before you switch it on:
- Meta changed to charging **per message** rather than per conversation, and since
  1 October 2026 each number gets **1,000 free service messages a month** (replies within
  24 hours of someone messaging you). **Login codes don't count** towards that free
  allowance.
- You need a verified business and an approved message template. Allow a couple of
  weeks.
- Most people go through a provider rather than Meta directly, and the provider adds
  its own fee on top. Compare that fee, not just Meta's rate.
- **Confirm the real Zimbabwe rate with Meta or a provider before you rely on my
  estimate.**

Until then, test mode is fine for you and a handful of farmers you can hand codes to
in person.

---

## 4. The order to do it

### Step A — Free trial run, this week ($0)

Goal: a real web address you can send to farmers on WhatsApp.

1. Put the code on GitHub (private is fine).
2. Make a free Render account, create a **Web Service** from the repository, pick
   **Frankfurt**.
3. Add a free Render **Postgres** database, and copy its connection details into the
   `POSTGRES_*` settings.
4. Set these in Render's environment settings:
   ```
   DJANGO_DEBUG=false
   DJANGO_SECRET_KEY=<a new long random one, not the laptop's>
   DJANGO_ALLOWED_HOSTS=your-app.onrender.com
   DJANGO_CSRF_TRUSTED_ORIGINS=https://your-app.onrender.com
   DJANGO_HTTPS=true
   DJANGO_BEHIND_PROXY=true
   DJANGO_CACHE_TABLE=murimi_cache
   DJANGO_ADMIN_PATH=<something only you know, not "admin">
   WHATSAPP_MODE=test
   ```
5. Build command: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate && python manage.py createcachetable`
6. Start command: `gunicorn config.wsgi` (add `gunicorn` to requirements.txt first).
7. **Change the staff password** before anyone else gets the address.

What you'll notice: the free service **goes to sleep after 15 minutes** and takes about
a minute to wake up, and the **free database is deleted 30 days after you make it**. It's
for showing people, not for real use. Don't let a farmer put real listings in it.

### Step B — The real thing (about $13/month)

1. Move the Render service to **Starter ($7)** so it stops sleeping.
2. Move the database to **Postgres Basic ($6)** so it isn't deleted.
3. Buy **murimi.co.zw** (about $3/year) and point it at Render. Add it to
   `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS`.
4. Set up photo storage (next step) **before** real farmers upload anything.
5. Once it's all working, raise `DJANGO_HSTS_SECONDS` from 3600 to 31536000 (a year).

### Step C — Photos must not vanish (free)

This one matters and is easy to miss. On Render, Railway and Fly, **the disk is wiped
every time you deploy**. Farmers' photos would disappear without warning.

Use **Cloudflare R2**: free up to **10 GB** of storage, and **free for people viewing
them**, which is the part that usually costs money elsewhere. Our photos are re-saved
at 1600px, so 10 GB is roughly 50,000 of them. Above that it's $0.015 per GB a month.

It needs `django-storages` and `boto3` added, and a few settings. Ask me and I'll do it
in about an hour. **Do this before Step B, not after.**

### Step D — Backups (free, and do not skip)

Render's paid Postgres keeps daily backups, but keep your own too: a weekly
`pg_dump` downloaded to your laptop. A backup you've never restored isn't a backup, so
try restoring one once.

### Step E — Only when people ask

- Real WhatsApp codes (Section 3).
- A privacy policy. You're keeping people's names and phone numbers, so you need one,
  and Zimbabwe's Data Protection Act applies. This is a lawyer question, not a code
  question, but it's cheap to get a simple one.
- Payments through Paynow (Section 1).
- Two-step login for staff accounts.

---

## 5. What's already done in the code

- `DEBUG` off by default; the app refuses to start without a secret key.
- HTTPS, secure cookies, HSTS and the proxy setting all switch on from `.env`
  (`DJANGO_HTTPS`, `DJANGO_BEHIND_PROXY`). See `.env.example`.
- The staff page can be moved off `/admin/` with `DJANGO_ADMIN_PATH`.
- PostgreSQL switches on by setting `POSTGRES_DB` and friends.
- `collectstatic` and WhiteNoise are set up, so CSS and JavaScript are served properly
  with no second web server.
- Rate-limit counts move to a shared database table with `DJANGO_CACHE_TABLE`, so
  several server processes share one count instead of one each.
- `python manage.py check --deploy` is clean apart from two optional HSTS extras
  (subdomains and preload), which only matter once you're sure every subdomain is HTTPS.

## 6. What is NOT done

- **Photo storage** (Step C). The most important gap.
- **No `gunicorn` in requirements.txt yet** — needed by every host above.
- **Staff accounts have no two-step login.**
- **The sample password `murimi-staff-2026` is in the code history.** Change it.
- **Sample data** (`seed_demo`, `seed_market`, `seed_orders`) must not be run on the
  real site. Only `migrate` and `createcachetable`.
- **No error reporting.** When something breaks for a farmer at 6 a.m. you won't know.
  Sentry's free plan covers 5,000 errors a month and takes ten minutes to add.

---

## 7. The honest answer on budget

For a very small budget, in order of what each dollar buys you:

1. **$0** — Render free + test-mode codes. Enough to show farmers and get their
   reaction, which is the thing you actually need next.
2. **$3/year** — the .co.zw name. Cheap, and makes it look real.
3. **$13/month** — the site stays awake and keeps its data. Only worth paying once
   somebody is using it.
4. **~$10 once** — WhatsApp codes for the first thousand sign-ups.

Stay on step 1 until farmers are asking you for a link. Nothing here expires or traps
you: everything above can be cancelled monthly.
