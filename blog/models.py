from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=100)
    category_image = models.ImageField(upload_to='blog_categories/', blank=True, null=True)
    class Meta: verbose_name = 'Blog Category'; verbose_name_plural = 'Blog Categories'
    def __str__(self): return self.name

class Post(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)
    def __str__(self): return self.title