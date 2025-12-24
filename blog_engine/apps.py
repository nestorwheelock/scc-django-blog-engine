"""Django app configuration for blog_engine."""
from django.apps import AppConfig


class BlogEngineConfig(AppConfig):
    """Configuration for the blog engine app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "blog_engine"
    verbose_name = "Blog Engine"

    def ready(self):
        """Import signals when app is ready."""
        try:
            from . import signals  # noqa: F401
        except ImportError:
            pass
