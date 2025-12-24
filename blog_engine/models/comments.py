"""
Comment and Reaction models for django-blog-engine.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone

from ..conf import blog_settings


class Comment(models.Model):
    """
    Comment on a post.

    Supports:
    - Threaded replies via parent field
    - Moderation workflow
    - Edit history tracking
    """

    post = models.ForeignKey(
        "blog_engine.Post",
        on_delete=models.CASCADE,
        related_name="comments",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="blog_comments",
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="replies",
    )
    body = models.TextField(max_length=blog_settings.COMMENT_MAX_LENGTH)
    is_approved = models.BooleanField(
        default=not blog_settings.MODERATE_COMMENTS,
        help_text="Whether comment is approved and visible",
    )
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    is_edited = models.BooleanField(default=False)
    edit_count = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["post", "is_approved", "created_at"]),
        ]

    def __str__(self):
        return f"Comment by {self.author} on {self.post}"

    @property
    def preview(self):
        """Return truncated body for admin display."""
        if len(self.body) > 100:
            return self.body[:100] + "..."
        return self.body

    @property
    def is_reply(self):
        """Check if this is a reply to another comment."""
        return self.parent is not None

    @property
    def thread_depth(self):
        """Calculate nesting depth of this comment."""
        depth = 0
        current = self.parent
        while current:
            depth += 1
            current = current.parent
        return depth

    def get_thread(self):
        """Return all comments in this thread (root + all replies)."""
        if self.parent:
            return self.parent.get_thread()
        return [self] + list(self._get_all_replies())

    def _get_all_replies(self):
        """Recursively get all replies."""
        replies = []
        for reply in self.replies.filter(is_deleted=False, is_approved=True):
            replies.append(reply)
            replies.extend(reply._get_all_replies())
        return replies

    def approve(self):
        """Approve the comment for display."""
        self.is_approved = True
        self.save(update_fields=["is_approved", "updated_at"])

    def reject(self):
        """Reject/unapprove the comment."""
        self.is_approved = False
        self.save(update_fields=["is_approved", "updated_at"])

    def soft_delete(self):
        """Soft delete the comment."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at", "updated_at"])

    def edit(self, new_body):
        """Edit the comment body and track the edit."""
        # Save history
        CommentHistory.objects.create(
            comment=self,
            body=self.body,
            edited_at=timezone.now(),
        )
        self.body = new_body
        self.is_edited = True
        self.edit_count += 1
        self.save(update_fields=["body", "is_edited", "edit_count", "updated_at"])


class PendingComment(models.Model):
    """
    Comment awaiting moderation.

    Used for anonymous/unauthenticated comment submissions
    that require approval before becoming full Comments.
    """

    post = models.ForeignKey(
        "blog_engine.Post",
        on_delete=models.CASCADE,
        related_name="pending_comments",
    )
    # For logged-in users awaiting moderation
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="pending_blog_comments",
    )
    # For anonymous commenters
    author_name = models.CharField(max_length=100, blank=True)
    author_email = models.EmailField(blank=True)
    author_url = models.URLField(blank=True)
    parent = models.ForeignKey(
        Comment,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="pending_replies",
    )
    body = models.TextField(max_length=blog_settings.COMMENT_MAX_LENGTH)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_comments",
    )
    rejection_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Pending Comment"
        verbose_name_plural = "Pending Comments"

    def __str__(self):
        author_display = self.author.username if self.author else self.author_name
        return f"Pending comment by {author_display}"

    def approve(self, reviewer):
        """
        Approve the pending comment and create a real Comment.

        Returns the created Comment instance.
        """
        comment = Comment.objects.create(
            post=self.post,
            author=self.author,
            parent=self.parent,
            body=self.body,
            is_approved=True,
        )
        self.reviewed_at = timezone.now()
        self.reviewed_by = reviewer
        self.save()
        self.delete()
        return comment

    def reject(self, reviewer, reason=""):
        """Mark the pending comment as rejected."""
        self.reviewed_at = timezone.now()
        self.reviewed_by = reviewer
        self.rejection_reason = reason
        self.save()
        self.delete()


class CommentHistory(models.Model):
    """
    Edit history for comments.

    Stores previous versions of comment body when edited.
    """

    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        related_name="history",
    )
    body = models.TextField()
    edited_at = models.DateTimeField()

    class Meta:
        ordering = ["-edited_at"]
        verbose_name = "Comment History"
        verbose_name_plural = "Comment History"

    def __str__(self):
        return f"Edit of comment {self.comment_id} at {self.edited_at}"


class Reaction(models.Model):
    """
    Reaction to a post (like, love, etc.).

    Supports multiple reaction types beyond simple likes.
    """

    REACTION_TYPES = blog_settings.REACTION_TYPES
    REACTION_CHOICES = [(r[0], r[1]) for r in REACTION_TYPES]

    post = models.ForeignKey(
        "blog_engine.Post",
        on_delete=models.CASCADE,
        related_name="reactions",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="blog_reactions",
    )
    reaction_type = models.CharField(
        max_length=20,
        choices=REACTION_CHOICES,
        default="LIKE",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["post", "user"]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} reacted {self.reaction_type} to {self.post}"

    @property
    def emoji(self):
        """Return the emoji for this reaction type."""
        for rtype, label, emoji in self.REACTION_TYPES:
            if rtype == self.reaction_type:
                return emoji
        return "👍"

    @classmethod
    def toggle(cls, post, user, reaction_type="LIKE"):
        """
        Toggle a reaction on a post.

        If user has same reaction, removes it.
        If user has different reaction, changes it.
        If user has no reaction, adds it.

        Returns (reaction_or_none, created_or_removed)
        """
        existing = cls.objects.filter(post=post, user=user).first()

        if existing:
            if existing.reaction_type == reaction_type:
                # Same reaction - remove it
                existing.delete()
                return None, "removed"
            else:
                # Different reaction - change it
                existing.reaction_type = reaction_type
                existing.save(update_fields=["reaction_type"])
                return existing, "changed"
        else:
            # No reaction - add it
            reaction = cls.objects.create(
                post=post,
                user=user,
                reaction_type=reaction_type,
            )
            return reaction, "created"
