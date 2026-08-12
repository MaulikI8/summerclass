from django.db import models
from django.contrib.auth.models import User

class SiteSetting(models.Model):
    site_title, meta_description, meta_keywords = models.CharField(max_length=200, default="MarketPlace"), models.TextField(blank=True, null=True), models.CharField(max_length=255, blank=True, null=True)
    logo, favicon, copyright = models.ImageField(upload_to="photos/logos/", blank=True, null=True), models.ImageField(upload_to="photos/favicons/", blank=True, null=True), models.CharField(max_length=200, blank=True, null=True)
    def __str__(self): return "Site Setting"

class Banner(models.Model):
    title, subtitle = models.CharField(max_length=200), models.TextField()
    badge_text, badge_icon = models.CharField(max_length=100, default="Official Student Hub"), models.CharField(max_length=50, default="fa-graduation-cap")
    theme_color = models.CharField(max_length=50, default='slide-blue', choices=[('slide-blue', 'Blue'), ('slide-green', 'Green'), ('slide-purple', 'Purple')])
    banner_image = models.ImageField(upload_to="banners/", blank=True, null=True)
    primary_btn_text, primary_btn_url = models.CharField(max_length=100, default="Explore Store"), models.CharField(max_length=255, default="/products/")
    secondary_btn_text, secondary_btn_url = models.CharField(max_length=100, blank=True, null=True, default="Sell an Item"), models.CharField(max_length=255, blank=True, null=True, default="/profile/?tab=add")
    order, is_active, created_at = models.PositiveIntegerField(default=0), models.BooleanField(default=True), models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['order', '-created_at']
    def __str__(self): return self.title

class Notification(models.Model):
    recipient, sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications'), models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_notifications')
    notif_type, title, message = models.CharField(max_length=30, default='system'), models.CharField(max_length=200), models.TextField(blank=True, default='')
    icon, link, is_read, created_at = models.CharField(max_length=50, default='fa-bell'), models.CharField(max_length=255, blank=True, default=''), models.BooleanField(default=False), models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['-created_at']
    def __str__(self): return self.title

    @classmethod
    def notify(cls, recipient, title, message='', notif_type='system', icon='fa-bell', link='', sender=None):
        return cls.objects.create(recipient=recipient, sender=sender, notif_type=notif_type, title=title, message=message, icon=icon, link=link)

    @classmethod
    def notify_all(cls, title, message='', notif_type='system', icon='fa-bell', link='', exclude_user=None):
        qs = User.objects.filter(is_active=True)
        if exclude_user: qs = qs.exclude(pk=exclude_user.pk)
        return cls.objects.bulk_create([cls(recipient=u, notif_type=notif_type, title=title, message=message, icon=icon, link=link) for u in qs])
