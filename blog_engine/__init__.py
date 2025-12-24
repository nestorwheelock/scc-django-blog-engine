"""
django-blog-engine - A modern Django blog engine.

Features:
- Content-addressed media storage with SHA256 deduplication
- Flexible visibility controls (public, private, friends, custom)
- AI enhancement tracking
- Scheduled publishing
- Threaded comments with moderation
- Multiple reaction types
- Hierarchical categories and flat tags
- EXIF metadata extraction
"""

__version__ = "0.1.0"
__author__ = "Nestor Wheelock"

default_app_config = "blog_engine.apps.BlogEngineConfig"
