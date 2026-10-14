"""
Helpers so every JSON answer from Murimi Market has the same shape as the Hub's:

    success:  {"status": "ok", ...}                         (any fields)
    failure:  {"error": "Plain message for people",
               "errors": {"field_name": "What's wrong with it"}}

The browser (api.js) can then always look in the same place for a message.
"""
from functools import wraps

from django.http import JsonResponse


def json_error(message, status=400, errors=None):
    """A failure answer: a message, per-field problems, and an HTTP status code.

    Common status codes we use:
      400 Bad Request        the form has problems (see "errors")
      401 Unauthorized       you need to log in
      403 Forbidden          you're logged in, but not allowed to do this
      404 Not Found          that thing doesn't exist
      405 Method Not Allowed wrong kind of request (e.g. POST where only GET works)
      409 Conflict           allowed, but not right now (e.g. already accepted)
      503 Service Unavailable  the server can't reach the database
    """
    return JsonResponse({"error": message, "errors": errors or {}}, status=status)


def allow(*methods):
    """Only let these HTTP methods through; anything else gets a JSON 405.

    Use it above a view:   @allow("GET")   or   @allow("GET", "POST")
    (Django has require_http_methods, but it answers with HTML, not our JSON shape.)
    """
    methods = {m.upper() for m in methods}

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if request.method not in methods:
                response = json_error(f"Use {' or '.join(sorted(methods))} for this address.", status=405)
                response["Allow"] = ", ".join(sorted(methods))   # HTTP rule: say which methods work
                return response
            return view(request, *args, **kwargs)
        return wrapper

    return decorator


def read_json(request):
    """The request body as a dict. Returns (data, None) or (None, error_response)."""
    import json
    if not request.body:
        return {}, None
    try:
        data = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None, json_error("The request wasn't valid JSON.", status=400)
    if not isinstance(data, dict):
        return None, json_error("Send a JSON object.", status=400)
    return data, None


def rate_limited(key, limit, seconds):
    """Count one try for `key`; True if it's over `limit` tries within `seconds`.

    Uses Django's cache (like the Hub: 5 log-in tries per 15 minutes).
    """
    from django.core.cache import cache
    cache.add(key, 0, timeout=seconds)          # start the window if it isn't there yet
    try:
        count = cache.incr(key)
    except ValueError:                           # expired between add and incr
        cache.set(key, 1, timeout=seconds)
        count = 1
    return count > limit


def client_ip(request):
    """Who is asking. Behind a hosting proxy every request seems to come from the proxy itself, so when
    DJANGO_BEHIND_PROXY is on we use the address the proxy appended LAST to X-Forwarded-For
    (earlier entries can be faked by the visitor). Off by default: never trust that header unless a proxy sets it."""
    from django.conf import settings
    if getattr(settings, "BEHIND_PROXY", False):
        parts = [p.strip() for p in request.META.get("HTTP_X_FORWARDED_FOR", "").split(",") if p.strip()]
        if parts:
            return parts[-1]
    return request.META.get("REMOTE_ADDR", "")


def throttle(request, name, limit, seconds, message="You're doing that a lot. Please wait a little and try again."):
    """Count one use of `name` for this person (or network address, if logged out).
    Returns a 429 answer when over `limit` uses in `seconds`, otherwise None. A cap like this stops one
    account from flooding farmers with offers or staff with reports."""
    who = request.user.id if request.user.is_authenticated else f"ip-{client_ip(request)}"
    if rate_limited(f"throttle:{name}:{who}", limit, seconds):
        return json_error(message, status=429)
    return None


def too_many_failures(key, limit):
    """True if `key` already has `limit` or more recorded failures (doesn't count anything)."""
    from django.core.cache import cache
    return (cache.get(key) or 0) >= limit


def record_failure(key, seconds):
    """Count one failure for `key`; the count disappears `seconds` after the first failure."""
    from django.core.cache import cache
    if not cache.add(key, 1, timeout=seconds):
        try:
            cache.incr(key)
        except ValueError:
            cache.set(key, 1, timeout=seconds)


def clear_failures(key):
    from django.core.cache import cache
    cache.delete(key)
