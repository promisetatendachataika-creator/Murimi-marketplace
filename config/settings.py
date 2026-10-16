"""
Settings for Murimi Marketplace.

Think of this file as the stall's rule book: which tools are on the table
(INSTALLED_APPS), which checks every customer passes through (MIDDLEWARE),
where the stock book lives (DATABASES), and where the front door map is
(ROOT_URLCONF).

Secrets are NOT written here. They come from the .env file (git-ignored),
the same habit as Murimi Intelligent Hub.
"""

import os
from pathlib import Path

# BASE_DIR = the project folder, e.g. C:\murimi-market
BASE_DIR = Path(__file__).resolve().parent.parent


def load_env_file(path):
    """Read KEY=value lines from .env into os.environ (tiny, no extra package).

    Values already set in the real environment win, so a server can override
    the file. Lines starting with # are comments.
    """
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env_file(BASE_DIR / ".env")


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


# --- Security -----------------------------------------------------------------
# The secret key signs session cookies and CSRF tokens. It lives in .env.
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
DEBUG = env_bool("DJANGO_DEBUG", False)

if not SECRET_KEY:
    if DEBUG:
        # Fine on your laptop only; start-windows.bat creates a real one in .env.
        SECRET_KEY = "dev-only-not-secret-change-me"
    else:
        raise RuntimeError("DJANGO_SECRET_KEY is missing. Put it in .env.")

ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
    if h.strip()
]


# --- Going live: HTTPS, proxies, admin address (all set in .env; nothing changes on your laptop) -----
# DJANGO_HTTPS=true      only when the site really is served over https:// (turns on secure cookies, redirect, HSTS)
# DJANGO_BEHIND_PROXY    true when a hosting proxy sits in front (it tells us the real address and http/https)
# DJANGO_ADMIN_PATH      move the staff back office off the well-known /admin/ address
# DJANGO_CSRF_TRUSTED_ORIGINS   e.g. https://market.example.com (needed on a real domain)
HTTPS = env_bool("DJANGO_HTTPS", False)
BEHIND_PROXY = env_bool("DJANGO_BEHIND_PROXY", False)
ADMIN_PATH = os.environ.get("DJANGO_ADMIN_PATH", "admin").strip("/ ") + "/"
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]
if BEHIND_PROXY:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
if HTTPS:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # HSTS tells browsers "only ever use https here". Start small (1 hour) so a mistake can be undone,
    # then raise to 31536000 (a year) once everything works.
    SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_HSTS_SECONDS", "3600"))
# Always on: never guess file types, never leak the page address to other sites, never allow framing.
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"


# --- Apps: the tools on the table -------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",         # the staff back office at /admin/
    "django.contrib.auth",          # users, passwords, permissions
    "django.contrib.contenttypes",  # lets permissions point at any table
    "django.contrib.sessions",      # "who is logged in" memory, stored in the DB
    "django.contrib.messages",      # one-time notices (used by the admin)
    "django.contrib.staticfiles",   # CSS / JS / images for the admin
    # Our own apps, one per job:
    "core",                         # /api/health/ and the shared JSON helpers
    "accounts",                     # users, log-in, WhatsApp codes
    "prices",                       # market prices and the fair-price meter
    "listings",                     # produce for sale, photos
    "buyer_requests",               # "I need 300 crates every week"
    "orders",                       # offers, orders, ratings
    "web",                          # serves the marketplace pages
]

# --- Middleware: checks every request walks through, in order -----------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",      # serves our CSS, JS and images when live
    "core.security.ContentSecurityPolicyMiddleware",   # tells browsers which scripts may run
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# A POST without a valid CSRF token is refused by middleware before any view runs.
# For /api/ addresses this view answers in our JSON shape (see core/api.py).
CSRF_FAILURE_VIEW = "core.api.csrf_failure"

# --- Accounts -----------------------------------------------------------------
# Our own User table (phone + optional username and email), set BEFORE the first migrate.
AUTH_USER_MODEL = "accounts.User"
# Log in with WhatsApp number, username or email.
AUTHENTICATION_BACKENDS = ["accounts.backends.PhoneUsernameEmailBackend"]
# "test" prints WhatsApp codes in the server window (like the Hub). "live" needs a Meta account.
WHATSAPP_MODE = os.environ.get("WHATSAPP_MODE", "test")
# Stay logged in for 30 days on your own phone; the cookie is hidden from JavaScript.
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
# Tests only: a fast password hasher (real passwords always use the slow, safe default).
import sys  # noqa: E402
if len(sys.argv) > 1 and sys.argv[1] == "test":
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Rate limits (log-in tries, codes) are counted in Django's cache.
# Rate limits (log-in tries, codes, spam caps) are counted here.
# On the laptop: this process's own memory. Live: set DJANGO_CACHE_TABLE in .env and run
#   python manage.py createcachetable
# so that several server processes share ONE count, instead of one each.
if os.environ.get("DJANGO_CACHE_TABLE"):
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.db.DatabaseCache",
                          "LOCATION": os.environ["DJANGO_CACHE_TABLE"]}}
else:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "murimi"}}

# The "front door map": the first urls.py Django reads for every request.
ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# --- Database: the stock book -------------------------------------------------
# SQLite (one file, db.sqlite3) on the laptop. If POSTGRES_DB is set in .env,
# PostgreSQL is used instead - the same switch as the Hub.
if os.environ.get("POSTGRES_DB"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ["POSTGRES_DB"],
            "USER": os.environ.get("POSTGRES_USER", ""),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
            "HOST": os.environ.get("POSTGRES_HOST", "127.0.0.1"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# --- Language and time --------------------------------------------------------
LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Africa/Harare"   # dates show in Zimbabwe time
USE_I18N = True
USE_TZ = True                 # the DB stores UTC; Django converts for display


STATIC_URL = "static/"
# Where `manage.py collectstatic` puts every CSS, JS and image file for a real server to serve.
# Nothing is needed on the laptop: with DEBUG on, Django finds them in each app's static/ folder.
STATIC_ROOT = BASE_DIR / "staticfiles"
# WhiteNoise lets Django serve those files itself, gzipped, so going live needs no second
# web server. We don't use its hashed-filename storage: the {% asset %} tag already adds
# ?v=<file time> to every link, which is what stops a browser using an old copy.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

# Uploaded files (listing photos). On the laptop Django serves them; when we go live,
# the web server or a storage service does.
MEDIA_URL = "/media/"
# Farmers' photos. On the laptop they sit in the project folder. On a real server the
# folder is WIPED on every deploy, so DJANGO_MEDIA_ROOT must point at a disk that survives
# (on Render: add a Disk, mount it at /var/data, and set DJANGO_MEDIA_ROOT=/var/data/media).
# Get this wrong and every farmer's photos disappear the next time you deploy.
MEDIA_ROOT = os.environ.get("DJANGO_MEDIA_ROOT") or (BASE_DIR / "media")
DATA_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024     # a form with photos may be up to ~12 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
