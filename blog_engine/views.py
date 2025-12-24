"""
Views for django-blog-engine.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
)

from .conf import blog_settings
from .models import Post, Category, Tag, Page, Comment, Reaction


class PostListView(ListView):
    """List published posts with pagination."""

    model = Post
    template_name = "blog_engine/post_list.html"
    context_object_name = "posts"
    paginate_by = blog_settings.POSTS_PER_PAGE

    def get_queryset(self):
        qs = Post.objects.filter(
            is_draft=False,
            is_deleted=False,
        ).select_related("author", "category").prefetch_related("tags", "media")

        # Filter by visibility
        user = self.request.user
        if user.is_authenticated:
            qs = qs.filter(
                Q(visibility="PUBLIC")
                | Q(visibility="UNLISTED")
                | Q(author=user)
                | Q(visibility="CUSTOM", allowed_users=user)
            ).distinct()
        else:
            qs = qs.filter(visibility__in=["PUBLIC", "UNLISTED"])

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = Category.objects.filter(is_active=True)
        context["tags"] = Tag.objects.all()[:20]
        return context


class PostDetailView(DetailView):
    """Display a single post."""

    model = Post
    template_name = "blog_engine/post_detail.html"
    context_object_name = "post"

    def get_object(self, queryset=None):
        # Support both pk and slug lookups
        if "slug" in self.kwargs:
            obj = get_object_or_404(Post, slug=self.kwargs["slug"])
        else:
            obj = get_object_or_404(Post, pk=self.kwargs["pk"])

        # Check visibility
        if not obj.can_view(self.request.user):
            raise Http404("Post not found")

        # Increment view count
        obj.increment_view_count()
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["comments"] = self.object.comments.filter(
            is_approved=True,
            is_deleted=False,
            parent=None,
        ).select_related("author")
        context["related_posts"] = self._get_related_posts()
        return context

    def _get_related_posts(self):
        """Get posts related by category or tags."""
        post = self.object
        related = Post.objects.filter(
            is_draft=False,
            is_deleted=False,
            visibility="PUBLIC",
        ).exclude(pk=post.pk)

        if post.category:
            related = related.filter(category=post.category)
        elif post.tags.exists():
            related = related.filter(tags__in=post.tags.all()).distinct()

        return related[:5]


class CategoryPostListView(PostListView):
    """List posts in a specific category."""

    template_name = "blog_engine/category_detail.html"

    def get_queryset(self):
        self.category = get_object_or_404(Category, slug=self.kwargs["slug"])
        return super().get_queryset().filter(category=self.category)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["category"] = self.category
        return context


class TagPostListView(PostListView):
    """List posts with a specific tag."""

    template_name = "blog_engine/tag_detail.html"

    def get_queryset(self):
        self.tag = get_object_or_404(Tag, slug=self.kwargs["slug"])
        return super().get_queryset().filter(tags=self.tag)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tag"] = self.tag
        return context


class PageDetailView(DetailView):
    """Display a static page."""

    model = Page
    template_name = "blog_engine/page_detail.html"
    context_object_name = "page"

    def get_queryset(self):
        return Page.objects.filter(is_published=True)


class AuthorPostListView(PostListView):
    """List posts by a specific author."""

    template_name = "blog_engine/author_posts.html"

    def get_queryset(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        self.author = get_object_or_404(User, username=self.kwargs["username"])
        return super().get_queryset().filter(author=self.author)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["author"] = self.author
        return context


class PostCreateView(LoginRequiredMixin, CreateView):
    """Create a new post."""

    model = Post
    template_name = "blog_engine/post_form.html"
    fields = ["title", "body", "excerpt", "category", "tags", "visibility", "is_draft"]

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)


class PostUpdateView(LoginRequiredMixin, UpdateView):
    """Edit an existing post."""

    model = Post
    template_name = "blog_engine/post_form.html"
    fields = [
        "title",
        "body",
        "excerpt",
        "category",
        "tags",
        "visibility",
        "is_draft",
        "is_pinned",
    ]

    def get_queryset(self):
        return Post.objects.filter(author=self.request.user)


class PostDeleteView(LoginRequiredMixin, DeleteView):
    """Soft delete a post."""

    model = Post
    template_name = "blog_engine/post_confirm_delete.html"
    success_url = "/"

    def get_queryset(self):
        return Post.objects.filter(author=self.request.user)

    def form_valid(self, form):
        self.object.soft_delete()
        return redirect(self.success_url)


class CommentCreateView(LoginRequiredMixin, View):
    """Add a comment to a post."""

    def post(self, request, pk):
        post = get_object_or_404(Post, pk=pk)

        if not post.allow_comments:
            return JsonResponse({"error": "Comments disabled"}, status=403)

        body = request.POST.get("body", "").strip()
        if not body:
            return JsonResponse({"error": "Comment body required"}, status=400)

        parent_id = request.POST.get("parent_id")
        parent = None
        if parent_id:
            parent = get_object_or_404(Comment, pk=parent_id, post=post)

        comment = Comment.objects.create(
            post=post,
            author=request.user,
            parent=parent,
            body=body,
            is_approved=not blog_settings.MODERATE_COMMENTS,
        )

        if request.headers.get("Accept") == "application/json":
            return JsonResponse({
                "id": comment.pk,
                "body": comment.body,
                "author": comment.author.username,
                "created_at": comment.created_at.isoformat(),
                "is_approved": comment.is_approved,
            })

        return redirect(post.get_absolute_url())


class ReactionToggleView(LoginRequiredMixin, View):
    """Toggle a reaction on a post."""

    def post(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        reaction_type = request.POST.get("reaction_type", "LIKE")

        reaction, action = Reaction.toggle(post, request.user, reaction_type)

        return JsonResponse({
            "action": action,
            "reaction_type": reaction.reaction_type if reaction else None,
            "total_reactions": post.reactions.count(),
        })


class FeedView(ListView):
    """RSS/Atom feed view."""

    model = Post
    template_name = "blog_engine/feed.xml"
    content_type = "application/rss+xml"
    paginate_by = 20

    def get_queryset(self):
        return Post.objects.filter(
            is_draft=False,
            is_deleted=False,
            visibility="PUBLIC",
        ).order_by("-created_at")

    def render_to_response(self, context, **response_kwargs):
        response_kwargs["content_type"] = self.content_type
        return super().render_to_response(context, **response_kwargs)
