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
