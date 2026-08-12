from django.contrib import admin
from django.utils.html import format_html
from .models import SiteSetting, Banner, Notification

@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    has_add_permission = lambda s, r: not SiteSetting.objects.exists()

@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'badge_text', 'order', 'is_active', 'image_preview')
    list_editable = ('order', 'is_active')
    image_preview = lambda s, o: format_html('<img src="{}" height="35"/>', o.banner_image.url) if o.banner_image else "—"

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'recipient', 'notif_type', 'is_read', 'created_at')
    list_filter = ('notif_type', 'is_read')
    list_editable = ('is_read',)
    actions = [lambda s, r, q: q.update(is_read=True)]
