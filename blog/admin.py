from django.contrib import admin
from .models import Category, Post

from django.utils.html import format_html

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'image_preview')
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.category_image:
            return format_html(
                '<img src="{}" width="60" height="60" style="object-fit:cover; border-radius:6px;" />',
                obj.category_image.url,
            )
        return "No image"

    image_preview.short_description = "Image"

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'category', 'created_at', 'status')
    list_filter = ('status', 'category')
    search_fields = ('title', 'content')
