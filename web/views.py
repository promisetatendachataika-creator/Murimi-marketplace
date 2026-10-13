from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie


@ensure_csrf_cookie
def index(request):
    """Serve the one marketplace page.

    @ensure_csrf_cookie makes Django put the 'csrftoken' cookie in the browser
    now, so later the page's JavaScript can copy it into the X-CSRFToken header
    when it sends offers and listings to /api/ (same as the Hub).
    """
    return render(request, "web/index.html")
