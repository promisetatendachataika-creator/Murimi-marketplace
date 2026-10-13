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

**Next:** Lesson 2: first app `core`, endpoint `/api/health/`, traced end to end, first test.
