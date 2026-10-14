"""
{% asset "web/app.js" %}  ->  /static/web/app.js?v=1791971234

Browsers keep copies of CSS and JavaScript files so pages load faster. When we
change a file, a browser may keep using its old copy, and an old api.js mixed
with a new app.js breaks the page. Adding ?v=<time the file last changed> gives
every new version a new address, so the browser fetches it fresh.
(When we go live, Django's ManifestStaticFilesStorage does the same job.)
"""
import os

from django import template
from django.contrib.staticfiles import finders
from django.templatetags.static import static

register = template.Library()


@register.simple_tag
def asset(path):
    url = static(path)
    found = finders.find(path)
    if found:
        url += "?v=%d" % int(os.path.getmtime(found))
    return url
