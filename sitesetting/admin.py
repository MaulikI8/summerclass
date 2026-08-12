from django.contrib import admin
from django.utils.html import format_html
from .models import SiteSetting, Banner, Notification

@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        if SiteSetting.objects.exists():
            return False
        return super().has_add_permission(request)


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'badge_text', 'theme_badge', 'order', 'is_active', 'image_preview')
    list_editable = ('order', 'is_active')
    list_filter = ('is_active', 'theme_color')
    search_fields = ('title', 'subtitle', 'badge_text')
    readonly_fields = ('image_preview',)

    fieldsets = (
        ('Header & Typography', {
            'fields': ('title', 'subtitle', 'badge_text', 'badge_icon', 'theme_color')
        }),
        ('Call-to-Action Buttons', {
            'fields': ('primary_btn_text', 'primary_btn_url', 'secondary_btn_text', 'secondary_btn_url')
        }),
        ('Media & Display Settings', {
            'fields': ('banner_image', 'image_preview', 'order', 'is_active')
        }),
    )

    def theme_badge(self, obj):
        colors = {
            'slide-blue': '#2563eb',
            'slide-green': '#10b981',
            'slide-purple': '#8b5cf6',
        }
        color = colors.get(obj.theme_color, '#2563eb')
        return format_html(
            '<span style="background:{}; color:#fff; padding:3px 10px; border-radius:12px; font-weight:600; font-size:0.75rem;">{}</span>',
            color,
            obj.get_theme_color_display()
        )
    theme_badge.short_description = "Theme"

    def image_preview(self, obj):
        if obj.banner_image:
            return format_html(
                '<img src="{}" width="100" height="50" style="object-fit:cover; border-radius:6px; border:1px solid #ddd;" />',
                obj.banner_image.url,
            )
        return "No image (Default Gradient)"
    image_preview.short_description = "Banner Preview"


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'recipient', 'notif_type', 'is_read', 'created_at')
    list_filter = ('notif_type', 'is_read', 'created_at')
    search_fields = ('title', 'message', 'recipient__username')
    list_editable = ('is_read',)
    readonly_fields = ('created_at',)
    actions = ['mark_as_read', 'mark_as_unread']

    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
    mark_as_read.short_description = "Mark selected as read"

    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)
    mark_as_unread.short_description = "Mark selected as unread"
