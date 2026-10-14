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
    "web",                          # serves the marketplace pages
]

# --- Middleware: checks every request walks through, in order -----------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
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

# Uploaded files (listing photos). On the laptop Django serves them; when we go live,
# the web server or a storage service does.
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DATA_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024     # a form with photos may be up to ~12 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
