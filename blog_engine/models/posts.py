"""
Post, Category, and Tag models for django-blog-engine.
"""
import hashlib

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from ..conf import blog_settings


class Category(models.Model):
    """
    Hierarchical category for organizing posts.

    Categories support nesting via parent field for tree structures.
    """

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
    )
    order = models.IntegerField(default=0, help_text="Display order within parent")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "name"]
        verbose_name_plural = "Categories"

    def __str__(self):
        if self.parent:
            return f"{self.parent} > {self.name}"
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:blog_settings.SLUG_MAX_LENGTH]
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("blog_engine:category_detail", kwargs={"slug": self.slug})

    @property
    def post_count(self):
        """Return count of published posts in this category."""
        return self.posts.filter(is_draft=False, is_deleted=False).count()

    def get_ancestors(self):
        """Return list of ancestor categories from root to parent."""
        ancestors = []
        current = self.parent
        while current:
            ancestors.insert(0, current)
            current = current.parent
        return ancestors

    def get_descendants(self):
        """Return all descendant categories."""
        descendants = list(self.children.all())
        for child in self.children.all():
            descendants.extend(child.get_descendants())
        return descendants


class Tag(models.Model):
    """
    Flat tag for posts.

    Tags are non-hierarchical and can be applied to multiple posts.
    """

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:blog_settings.SLUG_MAX_LENGTH]
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("blog_engine:tag_detail", kwargs={"slug": self.slug})

    @property
    def post_count(self):
        """Return count of published posts with this tag."""
        return self.posts.filter(is_draft=False, is_deleted=False).count()


class Post(models.Model):
    """
    Blog post / article.

    Supports:
    - Multiple visibility levels (public, private, friends, custom)
    - Scheduled publishing
    - AI enhancement tracking
    - Content hashing for deduplication
    """

    VISIBILITY_CHOICES = blog_settings.VISIBILITY_CHOICES

    # Content
    title = models.CharField(max_length=255, blank=True)
    slug = models.SlugField(max_length=255, blank=True, db_index=True)
    body = models.TextField()
    excerpt = models.TextField(
        blank=True,
        help_text="Optional manual excerpt. Auto-generated if blank.",
    )
    location = models.CharField(max_length=255, blank=True)

    # Author - uses Django's AUTH_USER_MODEL
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="blog_posts",
    )

    # Status
    visibility = models.CharField(
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default=blog_settings.DEFAULT_VISIBILITY,
    )
    is_draft = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    # Comments
    allow_comments = models.BooleanField(default=True)

    # Scheduled publishing
    scheduled_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Schedule post to be published at this time",
    )
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="When post was actually published",
    )

    # Deduplication
    content_hash = models.CharField(
        max_length=64,
        blank=True,
        db_index=True,
        help_text="SHA256 hash of normalized body for deduplication",
    )

    # AI Enhancement tracking
    ai_enhanced = models.BooleanField(
        default=False,
        help_text="Whether AI was used to enhance this post",
    )
    ai_instructions = models.TextField(
        blank=True,
        help_text="Instructions given to AI for content enhancement",
    )
    original_content = models.TextField(
        blank=True,
        help_text="Original content before AI enhancement",
    )

    # Taxonomy
    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="posts",
    )
    tags = models.ManyToManyField(Tag, related_name="posts", blank=True)

    # Custom visibility - specific users who can view
    allowed_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="allowed_blog_posts",
        help_text="Users who can view this post when visibility is CUSTOM",
    )

    # Engagement stats
    view_count = models.PositiveIntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_pinned", "-created_at"]
        indexes = [
            models.Index(fields=["visibility", "is_draft", "-created_at"]),
            models.Index(fields=["author", "-created_at"]),
        ]

    def __str__(self):
        if self.title:
            return self.title
        return f"{self.body[:50]}..." if len(self.body) > 50 else self.body

    def save(self, *args, **kwargs):
        # Auto-generate slug from title
        if not self.slug and self.title:
            base_slug = slugify(self.title)[:blog_settings.SLUG_MAX_LENGTH]
            slug = base_slug
            counter = 1
            while Post.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug

        # Set created_at if not set
        if not self.created_at:
            self.created_at = timezone.now()

        # Generate content hash for deduplication
        if self.body:
            normalized = self.body.lower().strip()
            self.content_hash = hashlib.sha256(normalized.encode()).hexdigest()

        # Set published_at when transitioning from draft
        if not self.is_draft and not self.published_at:
            self.published_at = timezone.now()

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        if self.slug:
            return reverse("blog_engine:post_detail_slug", kwargs={"slug": self.slug})
        return reverse("blog_engine:post_detail", kwargs={"pk": self.pk})

    @property
    def preview(self):
        """Return truncated body for feed display."""
        if self.excerpt:
            return self.excerpt
        if len(self.body) > 280:
            return self.body[:280] + "..."
        return self.body

    @property
    def first_media(self):
        """Return the first media item for thumbnails."""
        return self.media.order_by("order").first()

    @property
    def is_scheduled(self):
        """Check if post is scheduled for future publication."""
        if not self.is_draft or not self.scheduled_at:
            return False
        return self.scheduled_at > timezone.now()

    @property
    def time_until_publish(self):
        """Return timedelta until scheduled publish time."""
        if not self.is_scheduled:
            return None
        return self.scheduled_at - timezone.now()

    @property
    def is_published(self):
        """Check if post is published and visible."""
        return not self.is_draft and not self.is_deleted

    def can_view(self, user):
        """Check if user has permission to view this post."""
        # Drafts only visible to author
        if self.is_draft:
            return user.is_authenticated and user == self.author

        # Deleted posts not visible
        if self.is_deleted:
            return False

        # Public posts visible to all
        if self.visibility == "PUBLIC":
            return True

        # Unlisted posts visible if you have the link
        if self.visibility == "UNLISTED":
            return True

        # Must be authenticated for other visibility levels
        if not user.is_authenticated:
            return False

        # Author can always view
        if user == self.author:
            return True

        # Private only for author
        if self.visibility == "PRIVATE":
            return False

        # Custom visibility
        if self.visibility == "CUSTOM":
            return self.allowed_users.filter(pk=user.pk).exists()

        # Friends visibility - implement in your project
        # by overriding this method or using signals
        if self.visibility == "FRIENDS":
            return False  # Default deny, override as needed

        return False

    def publish(self):
        """Publish the post immediately."""
        self.is_draft = False
        self.published_at = timezone.now()
        self.save(update_fields=["is_draft", "published_at", "updated_at"])

    def archive(self):
        """Archive the post."""
        self.is_archived = True
        self.archived_at = timezone.now()
        self.save(update_fields=["is_archived", "archived_at", "updated_at"])

    def soft_delete(self):
        """Soft delete the post."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at", "updated_at"])

    def increment_view_count(self):
        """Increment view count atomically."""
        Post.objects.filter(pk=self.pk).update(view_count=models.F("view_count") + 1)


class Page(models.Model):
    """
    Static page (about, contact, etc.).

    Pages are similar to posts but don't appear in feeds.
    """

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    body = models.TextField()
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="blog_pages",
    )
    is_published = models.BooleanField(default=True)
    show_in_nav = models.BooleanField(
        default=False,
        help_text="Show in navigation menu",
    )
    nav_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nav_order", "title"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:blog_settings.SLUG_MAX_LENGTH]
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("blog_engine:page_detail", kwargs={"slug": self.slug})
