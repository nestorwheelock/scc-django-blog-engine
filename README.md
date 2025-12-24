# django-blog-engine

A modern Django blog engine with content-addressed media storage, AI enhancement tracking, and flexible visibility controls.

## Features

- **Content-Addressed Media Storage**: Files deduplicated via SHA256 hash - upload once, use everywhere
- **Flexible Visibility**: Public, Private, Unlisted, Friends-only, and Custom visibility levels
- **AI Enhancement Tracking**: Track when posts are AI-enhanced with original content preserved
- **Scheduled Publishing**: Schedule posts for future publication
- **Threaded Comments**: Nested comments with moderation workflow
- **Multiple Reactions**: Beyond simple likes - Love, Haha, Wow, Sad, Angry
- **Hierarchical Categories**: Nested category tree structure
- **Flat Tags**: Simple tag system for cross-cutting concerns
- **EXIF Extraction**: Automatic camera/GPS metadata from images
- **Static Pages**: Support for about, contact, and other static content

## Installation

```bash
pip install django-blog-engine
```

## Quick Start

1. Add to your `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    ...
    'blog_engine',
]
```

2. Include the URLs:

```python
# urls.py
from django.urls import path, include

urlpatterns = [
    ...
    path('blog/', include('blog_engine.urls')),
]
```

3. Run migrations:

```bash
python manage.py migrate
```

4. (Optional) Configure settings:

```python
# settings.py
BLOG_ENGINE = {
    'POSTS_PER_PAGE': 10,
    'MODERATE_COMMENTS': True,
    'DEFAULT_VISIBILITY': 'PUBLIC',
}
```

## Models

### Post
Blog posts with title, body, visibility, scheduling, and AI tracking.

### Category
Hierarchical categories for organizing posts.

### Tag
Flat tags for cross-cutting labels.

### Page
Static pages (about, contact, etc.).

### Comment
Threaded comments with moderation support.

### Reaction
Multiple reaction types on posts.

### MediaLibrary
Content-addressed media storage with deduplication.

### PostMedia
Junction table linking posts to media items.

## Configuration Options

```python
BLOG_ENGINE = {
    # Visibility
    'VISIBILITY_CHOICES': [
        ('PUBLIC', 'Public'),
        ('PRIVATE', 'Private'),
        ('UNLISTED', 'Unlisted'),
        ('FRIENDS', 'Friends Only'),
        ('CUSTOM', 'Custom'),
    ],
    'DEFAULT_VISIBILITY': 'PUBLIC',

    # Comments
    'ALLOW_ANONYMOUS_COMMENTS': False,
    'MODERATE_COMMENTS': True,
    'COMMENT_MAX_LENGTH': 5000,

    # Media
    'MEDIA_UPLOAD_PATH': 'blog/media/%Y/%m/',
    'MEDIA_MAX_SIZE_MB': 50,

    # Posts
    'POSTS_PER_PAGE': 10,
    'ALLOW_SCHEDULED_POSTS': True,
    'TRACK_AI_ENHANCEMENTS': True,

    # Reactions
    'REACTION_TYPES': [
        ('LIKE', 'Like', '👍'),
        ('LOVE', 'Love', '❤️'),
        ('HAHA', 'Haha', '😂'),
        ('WOW', 'Wow', '😮'),
        ('SAD', 'Sad', '😢'),
        ('ANGRY', 'Angry', '😠'),
    ],
}
```

## Templates

Override templates by creating files in `templates/blog_engine/`:

- `post_list.html` - Post listing page
- `post_detail.html` - Single post view
- `post_form.html` - Create/edit post form
- `category_detail.html` - Posts in category
- `tag_detail.html` - Posts with tag
- `page_detail.html` - Static page view

## Admin

All models have full Django admin support with:
- Inline media management
- Bulk actions (publish, archive, pin)
- Comment moderation
- Media preview thumbnails

## API

### Toggle Reaction
```javascript
fetch('/blog/post/123/react/', {
    method: 'POST',
    body: new URLSearchParams({ reaction_type: 'LOVE' }),
})
```

### Add Comment
```javascript
fetch('/blog/post/123/comment/', {
    method: 'POST',
    body: new URLSearchParams({ body: 'Great post!' }),
})
```

## License

MIT License - see LICENSE file.

## Author

Nestor Wheelock <nestor@nestorwheelock.com>
