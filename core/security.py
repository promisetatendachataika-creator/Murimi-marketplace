"""
Content-Security-Policy: a list that tells the browser which scripts, styles and pictures a page may load.
If someone ever managed to slip a <script> into a listing or a message, the browser would refuse to run it.
This is a second lock behind escaping every piece of user text (which the pages already do).

Applies to the marketplace pages and /api/. The staff back office (Django admin) is left alone
because it ships its own scripts.
"""
from django.conf import settings

POLICY = "; ".join([
    "default-src 'self'",
    "script-src 'self'",                                   # our own files only: no inline or outside scripts
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",   # inline style="" is used for bars and sizes
    "font-src 'self' https://fonts.gstatic.com",
    "img-src 'self' data: blob:",                          # blob:/data: = the photo previews on the Sell form
    "connect-src 'self'",
    "form-action 'self'",
    "base-uri 'self'",
    "object-src 'none'",
    "frame-ancestors 'none'",
])


class ContentSecurityPolicyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not request.path.startswith("/" + settings.ADMIN_PATH) and "Content-Security-Policy" not in response:
            response["Content-Security-Policy"] = POLICY
            response["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
        return response
