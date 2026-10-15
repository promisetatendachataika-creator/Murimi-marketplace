from django.shortcuts import render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import ensure_csrf_cookie


@ensure_csrf_cookie
def index(request):
    """Serve the one marketplace page.

    @ensure_csrf_cookie makes Django put the 'csrftoken' cookie in the browser
    now, so later the page's JavaScript can copy it into the X-CSRFToken header
    when it sends offers and listings to /api/ (same as the Hub).
    """
    return render(request, "web/index.html")


# The modes the account page can open in. Anything else falls back to "login".
AUTH_MODES = {"login", "register", "forgot"}


@ensure_csrf_cookie
def account_page(request, mode="login"):
    """Serve the log-in page: /login/, /register/ and /forgot/ share one template.

    The page shows the right form for `mode`; JavaScript (auth.js) can then
    switch between them without reloading. The CSRF cookie is set here too,
    because logging in is a POST that Django protects.
    """
    if mode not in AUTH_MODES:
        mode = "login"
    next_url = request.GET.get("next", "/")
    # Never send people to another website after log-in. Django's checker also catches the tricks a
    # plain startswith("/") misses: "/\\evil.com" and "/<tab>/evil.com", which browsers read as "//evil.com".
    if not next_url.startswith("/") or not url_has_allowed_host_and_scheme(
            next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        next_url = "/"
    return render(request, "web/login.html", {"mode": mode, "next": next_url})


@ensure_csrf_cookie
def my_account(request):
    """/account/ - offers on my produce, my listings, my orders.

    For now the page checks who is logged in with JavaScript (demo data).
    When real log-in exists, this view will add @login_required so the
    server itself sends logged-out visitors to /login/?next=/account/.
    """
    return render(request, "web/account.html")


@ensure_csrf_cookie
def listing_page(request, listing_id):
    """/listing/101/ - one listing in full.

    <int:listing_id> in urls.py means only numbers reach this view; /listing/abc/
    is a 404 before any of our code runs. Today the page fetches the listing
    with JavaScript (demo data). With the real database, this view will look it
    up first and answer 404 itself if it doesn't exist, and put the crop and
    price in the page's title, so a link shared on WhatsApp shows a preview.
    """
    return render(request, "web/listing.html", {"listing_id": listing_id})


def terms(request):
    """/terms/ - the rules for using Murimi Market. Plain HTML, nothing to work out."""
    return render(request, "web/terms.html")


def privacy(request):
    """/privacy/ - what we keep about people and who can see it."""
    return render(request, "web/privacy.html")
