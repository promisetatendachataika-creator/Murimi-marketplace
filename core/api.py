"""
JSON endpoints of the core app.

GET /api/health/   "Is the stall open, and can the stall keeper read the stock book?"
"""
import logging

from django.db import DatabaseError, connection
from django.http import JsonResponse
from django.utils import timezone

from .http import allow, json_error

log = logging.getLogger(__name__)

API_VERSION = "0.1"


@allow("GET")
def health(request):
    """Check the server is running and can talk to the database.

    The database check is one tiny SQL query:  SELECT 1
    It reads no table; it only proves the connection works.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")          # raw SQL, sent straight to SQLite (or PostgreSQL)
            (one,) = cursor.fetchone()          # the database answers with a row: (1,)
        database_ok = one == 1
    except DatabaseError:
        log.exception("Health check: database not reachable")
        database_ok = False

    if not database_ok:
        # 503 = "Service Unavailable": the server is up, but can't do its job right now.
        return JsonResponse(
            {"status": "error", "database": "unreachable", "error": "The database isn't answering. Please try again shortly.", "errors": {}},
            status=503,
        )

    return JsonResponse({
        "status": "ok",
        "database": "ok",
        "database_engine": connection.vendor,                    # "sqlite" today, "postgresql" later
        "server_time": timezone.localtime().isoformat(timespec="seconds"),   # Harare time (settings.TIME_ZONE)
        "version": API_VERSION,
    })


def not_found(request, rest=""):
    """Any /api/ address we don't have: answer in JSON, not Django's HTML 404 page."""
    return json_error(f"There's no API address /api/{rest}", status=404)


def csrf_failure(request, reason=""):
    """Django calls this when a POST arrives without a valid CSRF token (settings.CSRF_FAILURE_VIEW).

    The CSRF check is middleware: it runs BEFORE any view, so our @allow("GET") never
    gets a say. For /api/ we answer in our JSON shape so api.js can show a clear message;
    for normal pages we keep Django's own page.
    """
    if request.path.startswith("/api/"):
        return json_error("Your session has expired. Refresh the page and try again.", status=403)
    from django.views.csrf import csrf_failure as django_csrf_failure
    return django_csrf_failure(request, reason=reason)
