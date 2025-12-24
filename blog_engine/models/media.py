"""
Media library models for django-blog-engine.

Features content-addressed storage with SHA256 deduplication.
"""
import hashlib
import os

from django.conf import settings
from django.db import models

from ..conf import blog_settings


def get_upload_path(instance, filename):
    """Generate upload path for media files."""
    return blog_settings.MEDIA_UPLOAD_PATH + filename


class MediaLibrary(models.Model):
    """
    Central media library with content-based deduplication.

    Files are stored once and referenced by SHA256 content hash.
    Multiple posts can share the same file without re-uploading.
    """

    TYPE_CHOICES = [
        ("IMAGE", "Image"),
        ("VIDEO", "Video"),
        ("GIF", "GIF"),
        ("DOCUMENT", "Document"),
        ("AUDIO", "Audio"),
    ]

    file = models.FileField(upload_to=get_upload_path)
    content_hash = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="SHA256 hash of file content for deduplication",
    )
    media_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default="IMAGE")
    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(default=0, help_text="File size in bytes")
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    mime_type = models.CharField(max_length=100, blank=True)
    duration = models.FloatField(
        null=True,
        blank=True,
        help_text="Duration in seconds for video/audio",
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_blog_media",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # EXIF/Technical Metadata
    exif_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Raw EXIF data from image",
    )
    camera_make = models.CharField(max_length=100, blank=True)
    camera_model = models.CharField(max_length=100, blank=True)
    focal_length = models.CharField(max_length=50, blank=True)
    aperture = models.CharField(max_length=20, blank=True)
    shutter_speed = models.CharField(max_length=20, blank=True)
    iso = models.PositiveIntegerField(null=True, blank=True)

    # GPS Location
    gps_latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )
    gps_longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )

    # Capture date from EXIF
    capture_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Original date/time photo was taken",
    )

    # AI-generated metadata
    alt_text = models.TextField(
        blank=True,
        help_text="AI-generated or manual alt text for accessibility",
    )
    caption = models.TextField(
        blank=True,
        help_text="AI-generated or manual caption",
    )
    ai_tags = models.JSONField(
        default=list,
        blank=True,
        help_text="AI-detected tags/labels",
    )
    ai_description = models.TextField(
        blank=True,
        help_text="AI-generated detailed description",
    )

    # Tags for categorization
    tags = models.ManyToManyField(
        "blog_engine.Tag",
        blank=True,
        related_name="media_items",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Media Library Item"
        verbose_name_plural = "Media Library"

    def __str__(self):
        return f"{self.original_filename} ({self.media_type})"

    @property
    def file_url(self):
        """Return URL to the file."""
        if self.file:
            return self.file.url
        return None

    @property
    def file_extension(self):
        """Return file extension."""
        if self.original_filename:
            return os.path.splitext(self.original_filename)[1].lower()
        return ""

    @property
    def is_image(self):
        return self.media_type in ("IMAGE", "GIF")

    @property
    def is_video(self):
        return self.media_type == "VIDEO"

    @property
    def aspect_ratio(self):
        """Return aspect ratio as float."""
        if self.width and self.height:
            return self.width / self.height
        return None

    @property
    def orientation(self):
        """Return orientation based on dimensions."""
        if not self.width or not self.height:
            return "unknown"
        if self.width > self.height:
            return "landscape"
        elif self.height > self.width:
            return "portrait"
        return "square"

    @property
    def human_file_size(self):
        """Return human-readable file size."""
        size = self.file_size
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    @property
    def has_location(self):
        """Check if GPS coordinates are available."""
        return self.gps_latitude is not None and self.gps_longitude is not None

    @classmethod
    def get_or_create_from_file(cls, file_obj, uploaded_by=None):
        """
        Get existing media item or create new one based on content hash.

        This enables deduplication - same file uploaded twice
        returns the same MediaLibrary instance.

        Args:
            file_obj: Django UploadedFile or file-like object
            uploaded_by: User who uploaded the file

        Returns:
            (MediaLibrary instance, created boolean)
        """
        # Calculate hash
        hasher = hashlib.sha256()
        for chunk in file_obj.chunks():
            hasher.update(chunk)
        content_hash = hasher.hexdigest()

        # Check for existing
        existing = cls.objects.filter(content_hash=content_hash).first()
        if existing:
            return existing, False

        # Determine media type
        mime_type = getattr(file_obj, "content_type", "")
        if mime_type.startswith("image/gif"):
            media_type = "GIF"
        elif mime_type.startswith("image/"):
            media_type = "IMAGE"
        elif mime_type.startswith("video/"):
            media_type = "VIDEO"
        elif mime_type.startswith("audio/"):
            media_type = "AUDIO"
        else:
            media_type = "DOCUMENT"

        # Reset file position for save
        file_obj.seek(0)

        # Create new item
        item = cls.objects.create(
            file=file_obj,
            content_hash=content_hash,
            media_type=media_type,
            original_filename=file_obj.name,
            file_size=file_obj.size,
            mime_type=mime_type,
            uploaded_by=uploaded_by,
        )

        # Extract dimensions for images
        if media_type in ("IMAGE", "GIF"):
            item._extract_image_metadata()

        return item, True

    def _extract_image_metadata(self):
        """Extract dimensions and EXIF from image file."""
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS

            with Image.open(self.file.path) as img:
                self.width, self.height = img.size

                # Extract EXIF
                exif = img._getexif()
                if exif:
                    exif_data = {}
                    for tag_id, value in exif.items():
                        tag = TAGS.get(tag_id, tag_id)
                        # Convert bytes to string for JSON serialization
                        if isinstance(value, bytes):
                            try:
                                value = value.decode("utf-8", errors="ignore")
                            except Exception:
                                value = str(value)
                        exif_data[tag] = value

                    self.exif_data = exif_data
                    self.camera_make = exif_data.get("Make", "")
                    self.camera_model = exif_data.get("Model", "")
                    self.iso = exif_data.get("ISOSpeedRatings")

                self.save(
                    update_fields=[
                        "width",
                        "height",
                        "exif_data",
                        "camera_make",
                        "camera_model",
                        "iso",
                    ]
                )
        except Exception:
            pass  # Silently fail if can't extract metadata


class PostMedia(models.Model):
    """
    Junction table linking posts to media library items.

    Enables many-to-many between posts and media files.
    Same image can be attached to multiple posts.
    """

    post = models.ForeignKey(
        "blog_engine.Post",
        on_delete=models.CASCADE,
        related_name="media",
    )
    library_item = models.ForeignKey(
        MediaLibrary,
        on_delete=models.CASCADE,
        related_name="post_attachments",
    )
    order = models.IntegerField(default=0)
    custom_alt_text = models.CharField(
        max_length=500,
        blank=True,
        help_text="Custom alt text for this post (overrides library item)",
    )
    custom_caption = models.CharField(
        max_length=500,
        blank=True,
        help_text="Custom caption for this post",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "created_at"]
        verbose_name = "Post Media"
        verbose_name_plural = "Post Media"
        unique_together = ["post", "library_item"]

    def __str__(self):
        return f"{self.post} - {self.library_item.original_filename} #{self.order}"

    @property
    def effective_alt_text(self):
        """
        Return the best available alt text.

        Priority:
        1. Custom alt text on this PostMedia
        2. Alt text from MediaLibrary
        3. Fallback description
        """
        if self.custom_alt_text:
            return self.custom_alt_text
        if self.library_item.alt_text:
            return self.library_item.alt_text
        return f"Image: {self.library_item.original_filename}"

    @property
    def effective_caption(self):
        """Return custom caption or library item caption."""
        return self.custom_caption or self.library_item.caption

    # Delegate common properties to library_item
    @property
    def file_url(self):
        return self.library_item.file_url

    @property
    def width(self):
        return self.library_item.width

    @property
    def height(self):
        return self.library_item.height

    @property
    def is_image(self):
        return self.library_item.is_image

    @property
    def is_video(self):
        return self.library_item.is_video

    @property
    def media_type(self):
        return self.library_item.media_type
