from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Post

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'img_preview')
    def img_preview(self, o): return format_html('<img src="{}" width="50" height="50" style="object-fit:cover;border-radius:4px;" />', o.category_image.url) if o.category_image else "—"

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'category', 'created_at', 'status')
    list_filter = ('status', 'category')
    search_fields = ('title', 'content')
