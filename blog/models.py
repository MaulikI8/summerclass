from django.db import models
from django.contrib.auth.models import User

class Category(models.Model):
    name = models.CharField(max_length=100)
    category_image = models.ImageField(upload_to='blog_categories/', blank=True, null=True)
    class Meta: 
        verbose_name = 'Genre / Community'
        verbose_name_plural = 'Genres / Communities'
    def __str__(self): return self.name

class Post(models.Model):
    TAG_CHOICES = [('Discussion', 'Discussion'), ('Question', 'Question / Help'), ('Guide', 'Guide / Tips'), ('Review', 'Review')]
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='blog_posts')
    title = models.CharField(max_length=250)
    content = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='posts')
    tag = models.CharField(max_length=20, choices=TAG_CHOICES, default='Discussion')
    post_image = models.ImageField(upload_to='blogs/', blank=True, null=True)
    upvotes = models.ManyToManyField(User, related_name='upvoted_posts', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    class Meta: ordering = ['-created_at']
    def __str__(self): return self.title
    @property
    def upvote_count(self): return self.upvotes.count()
    @property
    def comment_count(self): return self.comments.count()

class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['created_at']
    def __str__(self): return f"{self.author.username} on {self.post.title}"