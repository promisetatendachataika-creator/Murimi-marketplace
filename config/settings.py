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
    "web",                          # serves the marketplace page
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
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
