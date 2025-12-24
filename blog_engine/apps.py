"""Django app configuration for blog_engine."""
from django.apps import AppConfig


class BlogEngineConfig(AppConfig):
    """Configuration for the blog engine app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "blog_engine"
    verbose_name = "Blog Engine"

    def ready(self):
        """Configure app when ready."""
        # Import signals if available
        try:
            from . import signals  # noqa: F401
        except ImportError:
            pass

        # Configure legacy table names if enabled
        from .conf import configure_legacy_tables
        configure_legacy_tables()
