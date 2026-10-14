# Lesson 3: The first JSON endpoint, `/api/health/`

## 1. Concept

A **JSON endpoint** is an address the page's JavaScript (not a person) asks for. Instead of an HTML page, the server answers with **data**:

```json
{"status": "ok", "database": "ok", "database_engine": "sqlite", "server_time": "2026-10-14T13:04:24+02:00", "version": "0.1"}
```

`/api/health/` answers one question: *"Is the stall open, and can the stall keeper read the stock book?"*
It is the smallest possible endpoint, so every step is easy to see. Later endpoints (listings, offers) follow exactly the same path.

## 2. The SQL

No table yet. The health check sends the database the smallest possible query:

```sql
SELECT 1;
```

It reads no table. It only proves the connection works: the database answers with one row, `(1,)`.
Django confirmed this is the **only** SQL the endpoint runs (a test checks it: `assertNumQueries(1)`).

## 3. The path of one request

```
PowerShell / browser
   │  GET /api/health/
   ▼
runserver ── config/settings.py (DEBUG, database, middleware list)
   │
   ▼
MIDDLEWARE, in order: security → session → common → CSRF → auth → messages → clickjacking
   │   (a POST without a CSRF token is stopped HERE, before any view: 403)
   ▼
config/urls.py      path("api/", include("core.urls"))       "starts with api/? → core"
   ▼
core/urls.py        path("health/", api.health)              "health/? → health()"
   ▼
core/http.py        @allow("GET")                            "not GET? → 405 JSON"
   ▼
core/api.py         health()  →  cursor.execute("SELECT 1")  →  SQLite answers (1,)
   ▼
JsonResponse({...})  →  200 OK, Content-Type: application/json
   ▼
back through middleware → PowerShell prints it / api.js reads it → footer: "Server: connected"
```

## 4. Try it (PowerShell, in the project folder, server running)

```powershell
# 1. The normal request
Invoke-RestMethod http://127.0.0.1:8000/api/health/

# 2. See the status code and headers too
curl.exe -i http://127.0.0.1:8000/api/health/

# 3. Wrong method: POST where only GET is allowed (no CSRF token → stopped by middleware)
curl.exe -i -X POST http://127.0.0.1:8000/api/health/

# 4. An address that doesn't exist
curl.exe -i http://127.0.0.1:8000/api/nothing-here/
```

What you should see:

| Request | Status | Body |
|---|---|---|
| `GET /api/health/` | `200 OK` | `{"status": "ok", "database": "ok", ...}` |
| `POST /api/health/` (no token) | `403 Forbidden` | `{"error": "Your session has expired. Refresh the page and try again.", "errors": {}}` |
| `POST` with the page's CSRF token | `405 Method Not Allowed` + `Allow: GET` | `{"error": "Use GET for this address.", "errors": {}}` |
| `GET /api/nothing-here/` | `404 Not Found` | `{"error": "There's no API address /api/nothing-here/", "errors": {}}` |
| Database down | `503 Service Unavailable` | `{"status": "error", "database": "unreachable", ...}` |

Every failure has the same shape as the Hub's: `{"error": "...", "errors": {field: message}}`.

## 5. What broke, and how we found it

The first POST test returned **403 with an HTML page**, not our JSON 405.
1. **Read the error:** 403 is Django's CSRF protection, which is middleware.
2. **What changed:** nothing in our code; the test client turns CSRF checks OFF, a real request doesn't.
3. **Reproduce:** `Client(enforce_csrf_checks=True)` gives the same 403.
4. **Fix one thing:** `CSRF_FAILURE_VIEW = "core.api.csrf_failure"` answers in our JSON shape for `/api/` addresses. Two new tests keep it that way.

Lesson: **middleware runs before your view.** If something is refused and your view's code never ran, look at middleware.

## 6. Tests (`core/tests.py`)

| Test | What it proves |
|---|---|
| `test_health_ok` | GET answers 200, JSON, status ok |
| `test_health_runs_one_sql_query` | Only one query (`SELECT 1`), so the check is cheap |
| `test_post_is_refused_in_our_json_shape` | Wrong method → 405, `Allow: GET`, our error shape |
| `test_database_down_gives_503` | Database down → 503 and a log line, not a crash |
| `test_post_without_csrf_token_is_refused_in_json` | Real-browser CSRF rules → 403 in JSON |
| `test_post_with_csrf_token_reaches_our_view` | With the token, the request reaches our view |
| `test_unknown_api_address_is_json_404` | Unknown `/api/...` → JSON 404 |
| `test_pages_outside_api_are_not_affected` | The catch-all doesn't break normal pages |

Run: `.venv\Scripts\python.exe manage.py test` (26 tests, all OK).

## 7. How it connects

| File | New / changed | Job |
|---|---|---|
| `core/apps.py` | new | Registers the app |
| `core/http.py` | new | `json_error()` and `@allow()`: one shape for every JSON answer |
| `core/api.py` | new | `health()`, `not_found()`, `csrf_failure()` |
| `core/urls.py` | new | `/api/health/` and the JSON 404 catch-all (must stay last) |
| `core/tests.py` | new | 8 tests |
| `config/settings.py` | changed | `"core"` in INSTALLED_APPS; `CSRF_FAILURE_VIEW` |
| `config/urls.py` | changed | `path("api/", include("core.urls"))`, before the pages |
| `web/static/web/api.js` | changed | `MarketAPI.health()`: the first real `fetch()` |
| `web/static/web/app.js` + `index.html` + `app.css` | changed | Footer shows "Server: connected" |

Link to earlier lessons: the same front door (`config/urls.py`) now sends `/api/...` to **core** and everything else to **web**. The waiter (`api.js`) made its first real trip; every `// LATER:` function will now become real the same way.
