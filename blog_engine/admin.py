"""
Django admin configuration for blog_engine.
"""
from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Category,
    Tag,
    Post,
    Page,
    Comment,
    PendingComment,
    Reaction,
    MediaLibrary,
    PostMedia,
)


class PostMediaInline(admin.TabularInline):
    """Inline for managing media attachments on posts."""

    model = PostMedia
    extra = 1
    raw_id_fields = ["library_item"]
    fields = ["library_item", "order", "custom_alt_text", "custom_caption"]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "parent", "slug", "post_count", "is_active", "order"]
    list_filter = ["is_active", "parent"]
    search_fields = ["name", "slug", "description"]
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ["order", "is_active"]
    ordering = ["parent__name", "order", "name"]


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "post_count", "created_at"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["created_at"]


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = [
        "title_preview",
        "author",
        "visibility",
        "is_draft",
        "is_pinned",
        "category",
        "view_count",
        "created_at",
    ]
    list_filter = [
        "visibility",
        "is_draft",
        "is_pinned",
        "is_archived",
        "is_deleted",
        "ai_enhanced",
        "category",
        "created_at",
    ]
    search_fields = ["title", "body", "author__username"]
    raw_id_fields = ["author", "category"]
    filter_horizontal = ["tags", "allowed_users"]
    date_hierarchy = "created_at"
    inlines = [PostMediaInline]
    readonly_fields = [
        "content_hash",
        "view_count",
        "created_at",
        "updated_at",
        "published_at",
    ]
    prepopulated_fields = {"slug": ("title",)}

    fieldsets = (
        (None, {
            "fields": ("title", "slug", "body", "excerpt", "author")
        }),
        ("Taxonomy", {
            "fields": ("category", "tags", "location")
        }),
        ("Visibility & Status", {
            "fields": (
                "visibility",
                "is_draft",
                "is_pinned",
                "allow_comments",
                "allowed_users",
            )
        }),
        ("Scheduling", {
            "fields": ("scheduled_at", "published_at"),
            "classes": ("collapse",),
        }),
        ("AI Enhancement", {
            "fields": ("ai_enhanced", "ai_instructions", "original_content"),
            "classes": ("collapse",),
        }),
        ("Metadata", {
            "fields": ("content_hash", "view_count", "created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    actions = ["publish_posts", "archive_posts", "pin_posts", "unpin_posts"]

    def title_preview(self, obj):
        """Truncated title for list display."""
        if obj.title:
            return obj.title[:60] + "..." if len(obj.title) > 60 else obj.title
        return obj.body[:40] + "..." if len(obj.body) > 40 else obj.body

    title_preview.short_description = "Title"

    @admin.action(description="Publish selected posts")
    def publish_posts(self, request, queryset):
        for post in queryset:
            post.publish()
        self.message_user(request, f"{queryset.count()} posts published.")

    @admin.action(description="Archive selected posts")
    def archive_posts(self, request, queryset):
        for post in queryset:
            post.archive()
        self.message_user(request, f"{queryset.count()} posts archived.")

    @admin.action(description="Pin selected posts")
    def pin_posts(self, request, queryset):
        queryset.update(is_pinned=True)
        self.message_user(request, f"{queryset.count()} posts pinned.")

    @admin.action(description="Unpin selected posts")
    def unpin_posts(self, request, queryset):
        queryset.update(is_pinned=False)
        self.message_user(request, f"{queryset.count()} posts unpinned.")


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ["title", "slug", "author", "is_published", "show_in_nav", "nav_order"]
    list_filter = ["is_published", "show_in_nav"]
    search_fields = ["title", "body"]
    prepopulated_fields = {"slug": ("title",)}
    list_editable = ["is_published", "show_in_nav", "nav_order"]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = [
        "preview",
        "author",
        "post",
        "is_approved",
        "is_edited",
        "created_at",
    ]
    list_filter = ["is_approved", "is_deleted", "is_edited", "created_at"]
    search_fields = ["body", "author__username", "post__title"]
    raw_id_fields = ["post", "author", "parent"]
    readonly_fields = ["edit_count", "created_at", "updated_at"]
    actions = ["approve_comments", "reject_comments"]

    @admin.action(description="Approve selected comments")
    def approve_comments(self, request, queryset):
        queryset.update(is_approved=True)
        self.message_user(request, f"{queryset.count()} comments approved.")

    @admin.action(description="Reject selected comments")
    def reject_comments(self, request, queryset):
        queryset.update(is_approved=False)
        self.message_user(request, f"{queryset.count()} comments rejected.")


@admin.register(PendingComment)
class PendingCommentAdmin(admin.ModelAdmin):
    list_display = [
        "body_preview",
        "get_author_display",
        "post",
        "ip_address",
        "created_at",
    ]
    list_filter = ["created_at"]
    search_fields = ["body", "author_name", "author_email"]
    raw_id_fields = ["post", "author", "parent"]
    readonly_fields = ["ip_address", "user_agent", "created_at"]
    actions = ["approve_pending", "reject_pending"]

    def body_preview(self, obj):
        return obj.body[:50] + "..." if len(obj.body) > 50 else obj.body

    body_preview.short_description = "Comment"

    def get_author_display(self, obj):
        if obj.author:
            return obj.author.username
        return obj.author_name or "Anonymous"

    get_author_display.short_description = "Author"

    @admin.action(description="Approve selected comments")
    def approve_pending(self, request, queryset):
        count = 0
        for pending in queryset:
            pending.approve(request.user)
            count += 1
        self.message_user(request, f"{count} comments approved.")

    @admin.action(description="Reject selected comments")
    def reject_pending(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"{count} comments rejected and deleted.")


@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    list_display = ["user", "post", "reaction_type", "emoji", "created_at"]
    list_filter = ["reaction_type", "created_at"]
    search_fields = ["user__username", "post__title"]
    raw_id_fields = ["user", "post"]


@admin.register(MediaLibrary)
class MediaLibraryAdmin(admin.ModelAdmin):
    list_display = [
        "thumbnail_preview",
        "original_filename",
        "media_type",
        "human_file_size",
        "dimensions",
        "uploaded_by",
        "created_at",
    ]
    list_filter = ["media_type", "created_at"]
    search_fields = ["original_filename", "alt_text", "caption"]
    readonly_fields = [
        "content_hash",
        "file_size",
        "width",
        "height",
        "mime_type",
        "exif_data",
        "created_at",
    ]
    filter_horizontal = ["tags"]

    fieldsets = (
        (None, {
            "fields": ("file", "original_filename", "media_type", "uploaded_by")
        }),
        ("Dimensions & Size", {
            "fields": ("width", "height", "file_size", "mime_type", "duration")
        }),
        ("AI/Manual Metadata", {
            "fields": ("alt_text", "caption", "ai_description", "ai_tags", "tags")
        }),
        ("Camera/EXIF", {
            "fields": (
                "camera_make",
                "camera_model",
                "focal_length",
                "aperture",
                "shutter_speed",
                "iso",
                "capture_date",
            ),
            "classes": ("collapse",),
        }),
        ("Location", {
            "fields": ("gps_latitude", "gps_longitude"),
            "classes": ("collapse",),
        }),
        ("System", {
            "fields": ("content_hash", "exif_data", "created_at"),
            "classes": ("collapse",),
        }),
    )

    def thumbnail_preview(self, obj):
        if obj.is_image and obj.file:
            return format_html(
                '<img src="{}" style="max-width: 50px; max-height: 50px;" />',
                obj.file.url,
            )
        return obj.media_type

    thumbnail_preview.short_description = "Preview"

    def dimensions(self, obj):
        if obj.width and obj.height:
            return f"{obj.width}x{obj.height}"
        return "-"

    dimensions.short_description = "Size"
