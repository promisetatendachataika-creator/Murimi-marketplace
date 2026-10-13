from django.apps import AppConfig


class WebConfig(AppConfig):
    """The 'web' app has one job: serve the marketplace page and its files."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "web"
