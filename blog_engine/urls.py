"""
URL configuration for django-blog-engine.

Include in your project urls.py:

    path('blog/', include('blog_engine.urls')),
"""
from django.urls import path

from . import views

app_name = "blog_engine"

urlpatterns = [
    # Post list and detail
    path("", views.PostListView.as_view(), name="post_list"),
    path("post/<int:pk>/", views.PostDetailView.as_view(), name="post_detail"),
    path("post/<slug:slug>/", views.PostDetailView.as_view(), name="post_detail_slug"),

    # Post CRUD
    path("post/new/", views.PostCreateView.as_view(), name="post_create"),
    path("post/<int:pk>/edit/", views.PostUpdateView.as_view(), name="post_update"),
    path("post/<int:pk>/delete/", views.PostDeleteView.as_view(), name="post_delete"),

    # Categories and tags
    path("category/<slug:slug>/", views.CategoryPostListView.as_view(), name="category_detail"),
    path("tag/<slug:slug>/", views.TagPostListView.as_view(), name="tag_detail"),

    # Authors
    path("author/<str:username>/", views.AuthorPostListView.as_view(), name="author_posts"),

    # Pages
    path("page/<slug:slug>/", views.PageDetailView.as_view(), name="page_detail"),

    # Interactions
    path("post/<int:pk>/comment/", views.CommentCreateView.as_view(), name="comment_create"),
    path("post/<int:pk>/react/", views.ReactionToggleView.as_view(), name="reaction_toggle"),

    # Feed
    path("feed/", views.FeedView.as_view(), name="feed"),
]
