"""
Tests for django-blog-engine models.
"""
import pytest
from django.contrib.auth import get_user_model

from blog_engine.models import (
    Post,
    Category,
    Tag,
    Comment,
    Reaction,
    MediaLibrary,
)

User = get_user_model()


@pytest.fixture
def user(db):
    """Create a test user."""
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
    )


@pytest.fixture
def category(db):
    """Create a test category."""
    return Category.objects.create(
        name="Test Category",
        slug="test-category",
    )


@pytest.fixture
def tag(db):
    """Create a test tag."""
    return Tag.objects.create(
        name="test-tag",
        slug="test-tag",
    )


@pytest.fixture
def post(db, user, category):
    """Create a test post."""
    return Post.objects.create(
        title="Test Post",
        body="This is a test post body.",
        author=user,
        category=category,
        visibility="PUBLIC",
    )


class TestCategory:
    """Tests for Category model."""

    def test_create_category(self, db):
        """Test creating a category."""
        cat = Category.objects.create(name="My Category")
        assert cat.name == "My Category"
        assert cat.slug == "my-category"

    def test_category_hierarchy(self, db, category):
        """Test nested categories."""
        child = Category.objects.create(
            name="Child Category",
            parent=category,
        )
        assert child.parent == category
        assert str(child) == "Test Category > Child Category"

    def test_get_ancestors(self, db, category):
        """Test getting category ancestors."""
        child = Category.objects.create(name="Child", parent=category)
        grandchild = Category.objects.create(name="Grandchild", parent=child)

        ancestors = grandchild.get_ancestors()
        assert len(ancestors) == 2
        assert ancestors[0] == category
        assert ancestors[1] == child


class TestTag:
    """Tests for Tag model."""

    def test_create_tag(self, db):
        """Test creating a tag."""
        tag = Tag.objects.create(name="Django")
        assert tag.name == "Django"
        assert tag.slug == "django"

    def test_tag_post_count(self, db, tag, post):
        """Test tag post count property."""
        post.tags.add(tag)
        assert tag.post_count == 1


class TestPost:
    """Tests for Post model."""

    def test_create_post(self, db, user):
        """Test creating a post."""
        post = Post.objects.create(
            title="Hello World",
            body="My first post!",
            author=user,
        )
        assert post.title == "Hello World"
        assert post.slug == "hello-world"
        assert post.is_published

    def test_post_preview(self, db, user):
        """Test post preview truncation."""
        post = Post.objects.create(
            title="Test",
            body="x" * 500,
            author=user,
        )
        assert len(post.preview) == 283  # 280 + "..."

    def test_post_visibility_public(self, db, post, user):
        """Test public post visibility."""
        assert post.can_view(None)  # Anonymous can view
        assert post.can_view(user)  # Author can view

    def test_post_visibility_private(self, db, user):
        """Test private post visibility."""
        post = Post.objects.create(
            title="Private",
            body="Secret",
            author=user,
            visibility="PRIVATE",
        )
        other_user = User.objects.create_user(
            username="other",
            password="pass",
        )
        assert post.can_view(user)  # Author can view
        assert not post.can_view(other_user)  # Other cannot

    def test_post_draft_visibility(self, db, user):
        """Test draft post visibility."""
        post = Post.objects.create(
            title="Draft",
            body="Work in progress",
            author=user,
            is_draft=True,
        )
        other_user = User.objects.create_user(
            username="other",
            password="pass",
        )
        assert post.can_view(user)  # Author can view drafts
        assert not post.can_view(other_user)  # Others cannot

    def test_content_hash_deduplication(self, db, user):
        """Test content hash generation."""
        post1 = Post.objects.create(
            title="Post 1",
            body="Same content",
            author=user,
        )
        post2 = Post.objects.create(
            title="Post 2",
            body="Same content",
            author=user,
        )
        # Same content = same hash
        assert post1.content_hash == post2.content_hash

    def test_publish_post(self, db, user):
        """Test publishing a draft post."""
        post = Post.objects.create(
            title="Draft",
            body="Content",
            author=user,
            is_draft=True,
        )
        assert not post.is_published

        post.publish()
        post.refresh_from_db()

        assert post.is_published
        assert post.published_at is not None


class TestComment:
    """Tests for Comment model."""

    def test_create_comment(self, db, post, user):
        """Test creating a comment."""
        comment = Comment.objects.create(
            post=post,
            author=user,
            body="Great post!",
        )
        assert comment.body == "Great post!"
        assert comment.post == post

    def test_threaded_comments(self, db, post, user):
        """Test nested comment replies."""
        parent = Comment.objects.create(
            post=post,
            author=user,
            body="Parent comment",
        )
        reply = Comment.objects.create(
            post=post,
            author=user,
            body="Reply",
            parent=parent,
        )
        assert reply.is_reply
        assert reply.thread_depth == 1
        assert parent.replies.count() == 1

    def test_edit_comment(self, db, post, user):
        """Test editing a comment with history."""
        comment = Comment.objects.create(
            post=post,
            author=user,
            body="Original",
        )
        comment.edit("Updated content")

        assert comment.body == "Updated content"
        assert comment.is_edited
        assert comment.edit_count == 1
        assert comment.history.count() == 1
        assert comment.history.first().body == "Original"


class TestReaction:
    """Tests for Reaction model."""

    def test_toggle_reaction_create(self, db, post, user):
        """Test creating a reaction."""
        reaction, action = Reaction.toggle(post, user, "LIKE")

        assert action == "created"
        assert reaction.reaction_type == "LIKE"
        assert post.reactions.count() == 1

    def test_toggle_reaction_remove(self, db, post, user):
        """Test removing a reaction by toggling same type."""
        Reaction.toggle(post, user, "LIKE")
        reaction, action = Reaction.toggle(post, user, "LIKE")

        assert action == "removed"
        assert reaction is None
        assert post.reactions.count() == 0

    def test_toggle_reaction_change(self, db, post, user):
        """Test changing reaction type."""
        Reaction.toggle(post, user, "LIKE")
        reaction, action = Reaction.toggle(post, user, "LOVE")

        assert action == "changed"
        assert reaction.reaction_type == "LOVE"
        assert post.reactions.count() == 1


class TestMediaLibrary:
    """Tests for MediaLibrary model."""

    def test_human_file_size(self, db, user):
        """Test human-readable file size."""
        media = MediaLibrary.objects.create(
            content_hash="abc123",
            original_filename="test.jpg",
            file_size=1536000,  # 1.5 MB
            uploaded_by=user,
        )
        assert "MB" in media.human_file_size

    def test_orientation_detection(self, db, user):
        """Test image orientation detection."""
        landscape = MediaLibrary.objects.create(
            content_hash="land123",
            original_filename="landscape.jpg",
            width=1920,
            height=1080,
            uploaded_by=user,
        )
        portrait = MediaLibrary.objects.create(
            content_hash="port123",
            original_filename="portrait.jpg",
            width=1080,
            height=1920,
            uploaded_by=user,
        )
        square = MediaLibrary.objects.create(
            content_hash="sq123",
            original_filename="square.jpg",
            width=1000,
            height=1000,
            uploaded_by=user,
        )

        assert landscape.orientation == "landscape"
        assert portrait.orientation == "portrait"
        assert square.orientation == "square"
