from django.contrib import admin
from django.utils.html import format_html
from .models import SiteSetting, Banner, Notification

@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not SiteSetting.objects.exists() and super().has_add_permission(request)

@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'badge_text', 'theme_badge', 'order', 'is_active', 'image_preview')
    list_editable = ('order', 'is_active')
    list_filter = ('is_active', 'theme_color')
    search_fields = ('title', 'subtitle', 'badge_text')
    readonly_fields = ('image_preview',)

    def theme_badge(self, obj):
        colors = {'slide-blue': '#2563eb', 'slide-green': '#10b981', 'slide-purple': '#8b5cf6'}
        return format_html('<span style="background:{};color:#fff;padding:2px 8px;border-radius:10px;font-size:0.75rem;">{}</span>', colors.get(obj.theme_color, '#2563eb'), obj.get_theme_color_display())
    theme_badge.short_description = "Theme"

    def image_preview(self, obj):
        return format_html('<img src="{}" width="80" height="40" style="object-fit:cover;border-radius:4px;" />', obj.banner_image.url) if obj.banner_image else "Default Gradient"
    image_preview.short_description = "Preview"

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'recipient', 'notif_type', 'is_read', 'created_at')
    list_filter = ('notif_type', 'is_read')
    search_fields = ('title', 'message', 'recipient__username')
    list_editable = ('is_read',)
    actions = ['mark_read', 'mark_unread']

    def mark_read(self, request, qs): qs.update(is_read=True)
    def mark_unread(self, request, qs): qs.update(is_read=False)
