from django.db import models
from django.contrib.auth.models import User

class SiteSetting(models.Model):
    site_title = models.CharField(max_length=200, default="MarketPlace")
    meta_description = models.TextField(blank=True, null=True)
    meta_keywords = models.CharField(max_length=255, blank=True, null=True)
    logo = models.ImageField(upload_to="photos/logos/", blank=True, null=True)
    favicon = models.ImageField(upload_to="photos/favicons/", blank=True, null=True)
    copyright = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self): return "Site Setting"
    class Meta:
        verbose_name = "Site Setting"
        verbose_name_plural = "Site Settings"

class Banner(models.Model):
    title = models.CharField(max_length=200)
    subtitle = models.TextField()
    badge_text = models.CharField(max_length=100, default="Official Student Hub")
    badge_icon = models.CharField(max_length=50, default="fa-graduation-cap")
    theme_color = models.CharField(max_length=50, default='slide-blue', choices=[('slide-blue', 'Ocean Blue'), ('slide-green', 'Emerald Green'), ('slide-purple', 'Royal Purple')])
    banner_image = models.ImageField(upload_to="banners/", blank=True, null=True)
    primary_btn_text = models.CharField(max_length=100, default="Explore Store")
    primary_btn_url = models.CharField(max_length=255, default="/products/")
    secondary_btn_text = models.CharField(max_length=100, blank=True, null=True, default="Sell an Item")
    secondary_btn_url = models.CharField(max_length=255, blank=True, null=True, default="/profile/?tab=add")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', '-created_at']
        verbose_name = "Hero Banner Slide"
        verbose_name_plural = "Hero Banner Slides"

    def __str__(self): return self.title

class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_notifications')
    notif_type = models.CharField(max_length=30, default='system')
    title = models.CharField(max_length=200)
    message = models.TextField(blank=True, default='')
    icon = models.CharField(max_length=50, default='fa-bell')
    link = models.CharField(max_length=255, blank=True, default='')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self): return self.title

    @classmethod
    def notify(cls, recipient, title, message='', notif_type='system', icon='fa-bell', link='', sender=None):
        return cls.objects.create(recipient=recipient, sender=sender, notif_type=notif_type, title=title, message=message, icon=icon, link=link)

    @classmethod
    def notify_all(cls, title, message='', notif_type='system', icon='fa-bell', link='', exclude_user=None):
        users = User.objects.filter(is_active=True)
        if exclude_user: users = users.exclude(pk=exclude_user.pk)
        return cls.objects.bulk_create([cls(recipient=u, notif_type=notif_type, title=title, message=message, icon=icon, link=link) for u in users])
