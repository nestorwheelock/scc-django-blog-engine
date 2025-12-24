"""
Configuration settings for django-blog-engine.

Override these in your Django settings.py:

    BLOG_ENGINE = {
        'VISIBILITY_CHOICES': [...],
        'DEFAULT_VISIBILITY': 'PUBLIC',
        'ALLOW_ANONYMOUS_COMMENTS': False,
        ...
    }
"""
from django.conf import settings

DEFAULTS = {
    # Visibility options for posts
    "VISIBILITY_CHOICES": [
        ("PUBLIC", "Public"),
        ("PRIVATE", "Private"),
        ("UNLISTED", "Unlisted"),
        ("FRIENDS", "Friends Only"),
        ("CUSTOM", "Custom"),
    ],
    "DEFAULT_VISIBILITY": "PUBLIC",

    # Comments
    "ALLOW_ANONYMOUS_COMMENTS": False,
    "MODERATE_COMMENTS": True,
    "COMMENT_MAX_LENGTH": 5000,

    # Media
    "MEDIA_UPLOAD_PATH": "blog/media/%Y/%m/",
    "MEDIA_MAX_SIZE_MB": 50,
    "ALLOWED_IMAGE_TYPES": ["image/jpeg", "image/png", "image/gif", "image/webp"],
    "ALLOWED_VIDEO_TYPES": ["video/mp4", "video/webm"],
    "GENERATE_THUMBNAILS": True,
    "THUMBNAIL_SIZES": [(150, 150), (300, 300), (600, 600)],

    # Posts
    "POSTS_PER_PAGE": 10,
    "ALLOW_SCHEDULED_POSTS": True,
    "TRACK_AI_ENHANCEMENTS": True,

    # Reactions
    "REACTION_TYPES": [
        ("LIKE", "Like", "👍"),
        ("LOVE", "Love", "❤️"),
        ("HAHA", "Haha", "😂"),
        ("WOW", "Wow", "😮"),
        ("SAD", "Sad", "😢"),
        ("ANGRY", "Angry", "😠"),
    ],

    # SEO
    "AUTO_GENERATE_SLUGS": True,
    "SLUG_MAX_LENGTH": 100,
}


class BlogEngineSettings:
    """
    Lazy settings object that reads from Django settings.

    Access via: from blog_engine.conf import blog_settings
    """

    def __getattr__(self, name):
        if name not in DEFAULTS:
            raise AttributeError(f"Invalid blog_engine setting: {name}")

        user_settings = getattr(settings, "BLOG_ENGINE", {})
        return user_settings.get(name, DEFAULTS[name])

    @property
    def VISIBILITY_CHOICES(self):
        """Return visibility choices as a list of tuples."""
        user_settings = getattr(settings, "BLOG_ENGINE", {})
        return user_settings.get("VISIBILITY_CHOICES", DEFAULTS["VISIBILITY_CHOICES"])


blog_settings = BlogEngineSettings()
