"""
Configuration settings for django-blog-engine.

Override these in your Django settings.py:

    BLOG_ENGINE = {
        'VISIBILITY_CHOICES': [...],
        'DEFAULT_VISIBILITY': 'PUBLIC',
        'ALLOW_ANONYMOUS_COMMENTS': False,
        ...
    }

For migrating from existing tables, use:

    BLOG_ENGINE = {
        'USE_LEGACY_TABLE_NAMES': True,
        'LEGACY_TABLE_PREFIX': 'posts',  # uses posts_category, posts_post, etc.
    }
"""
from django.conf import settings

DEFAULTS = {
    # Legacy table support for migrations
    "USE_LEGACY_TABLE_NAMES": False,
    "LEGACY_TABLE_PREFIX": "posts",  # e.g., posts_category, posts_post

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


def get_table_name(model_name):
    """
    Get the database table name for a model.

    If USE_LEGACY_TABLE_NAMES is True, returns legacy table name
    (e.g., 'posts_post' instead of 'blog_engine_post').

    Args:
        model_name: lowercase model name (e.g., 'post', 'category')

    Returns:
        Table name string
    """
    if blog_settings.USE_LEGACY_TABLE_NAMES:
        prefix = blog_settings.LEGACY_TABLE_PREFIX
        return f"{prefix}_{model_name}"
    return f"blog_engine_{model_name}"


def configure_legacy_tables():
    """
    Configure blog_engine models to use legacy table names.

    Call this from AppConfig.ready() if USE_LEGACY_TABLE_NAMES is True.
    This modifies the model _meta.db_table at runtime.
    """
    if not blog_settings.USE_LEGACY_TABLE_NAMES:
        return

    from . import models

    # Map of model class to legacy table name suffix
    model_map = {
        models.Category: "category",
        models.Tag: "tag",
        models.Post: "post",
        models.Page: "page",
        models.Comment: "comment",
        models.PendingComment: "pendingcomment",
        models.CommentHistory: "commenthistory",
        models.Reaction: "reaction",
        models.MediaLibrary: "medialibrary",
        models.PostMedia: "postmedia",
    }

    prefix = blog_settings.LEGACY_TABLE_PREFIX

    for model_class, table_suffix in model_map.items():
        model_class._meta.db_table = f"{prefix}_{table_suffix}"
        # Also mark as managed=False to prevent migration conflicts
        model_class._meta.managed = False

    # Configure M2M through-tables
    # Post.tags -> posts_post_tags
    post_tags_field = models.Post._meta.get_field("tags")
    if hasattr(post_tags_field, "remote_field") and post_tags_field.remote_field.through:
        through_model = post_tags_field.remote_field.through
        through_model._meta.db_table = f"{prefix}_post_tags"
        through_model._meta.managed = False

    # Post.allowed_users -> posts_post_allowed_users
    allowed_users_field = models.Post._meta.get_field("allowed_users")
    if hasattr(allowed_users_field, "remote_field") and allowed_users_field.remote_field.through:
        through_model = allowed_users_field.remote_field.through
        through_model._meta.db_table = f"{prefix}_post_allowed_users"
        through_model._meta.managed = False

    # MediaLibrary.tags -> posts_medialibrary_tags
    media_tags_field = models.MediaLibrary._meta.get_field("tags")
    if hasattr(media_tags_field, "remote_field") and media_tags_field.remote_field.through:
        through_model = media_tags_field.remote_field.through
        through_model._meta.db_table = f"{prefix}_medialibrary_tags"
        through_model._meta.managed = False
