from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import Category, Post

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'img_preview')
    def img_preview(self, o):
        try:
            if o.category_image:
                return format_html('<img src="{}" width="50" height="50" style="object-fit:cover;border-radius:6px;" />', o.category_image.url)
        except Exception:
            pass
        return mark_safe('<span style="color:#94a3b8;font-size:11px;">—</span>')

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('img_preview', 'title', 'author', 'category', 'created_at', 'status')
    list_filter = ('status', 'category', 'created_at')
    search_fields = ('title', 'content', 'author__username', 'author__email')
    
    def img_preview(self, o):
        try:
            if o.post_image:
                return format_html('<img src="{}" width="50" height="50" style="object-fit:cover;border-radius:6px;" />', o.post_image.url)
        except Exception:
            pass
        return mark_safe('<span style="color:#94a3b8;font-size:11px;">No photo</span>')
    img_preview.short_description = "Image"
