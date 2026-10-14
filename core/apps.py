from django.apps import AppConfig


class CoreConfig(AppConfig):
    """The 'core' app: small pieces every other app uses.

    - api.py   the /api/health/ check, and the "not found" answer for /api/
    - http.py  helpers that make every JSON answer look the same
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        from . import admin_dashboard
        admin_dashboard.install()
        import sys
        if len(sys.argv) > 1 and sys.argv[1] == "test":
            # Tests only: rate-limit counts live in the cache, so start every test with an empty one.
            # (Otherwise one test's "30 offers this hour" would leak into the next.)
            from django.core.cache import cache
            from django.test import SimpleTestCase
            original = SimpleTestCase._setup_and_call

            def clean_run(test, result, debug=False):
                cache.clear()
                original(test, result, debug)
            SimpleTestCase._setup_and_call = clean_run