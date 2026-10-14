from django.apps import AppConfig


class CoreConfig(AppConfig):
    """The 'core' app: small pieces every other app uses.

    - api.py   the /api/health/ check, and the "not found" answer for /api/
    - http.py  helpers that make every JSON answer look the same
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
