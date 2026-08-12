from django.db import models

class SiteSetting(models.Model):
    site_title = models.CharField(max_length=200, default="MarketPlace")
    meta_description = models.TextField(blank=True, null=True)
    meta_keywords = models.CharField(max_length=255, blank=True, null=True)
    logo = models.ImageField(upload_to="photos/logos/", blank=True, null=True)
    favicon = models.ImageField(upload_to="photos/favicons/", blank=True, null=True)
    copyright = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return "Site Setting"

    class Meta:
        verbose_name = "Site Setting"
        verbose_name_plural = "Site Settings"


class Banner(models.Model):
    THEME_CHOICES = [
        ('slide-blue', 'Ocean Blue Gradient'),
        ('slide-green', 'Emerald Green Gradient'),
        ('slide-purple', 'Royal Purple Gradient'),
    ]

    title = models.CharField(max_length=200, help_text="Main heading of the hero slide")
    subtitle = models.TextField(help_text="Short descriptive paragraph below the title")
    badge_text = models.CharField(max_length=100, default="Official Student Hub", help_text="Badge tag above heading")
    badge_icon = models.CharField(max_length=50, default="fa-graduation-cap", help_text="Font Awesome icon class (e.g. fa-graduation-cap, fa-tags, fa-bolt)")
    theme_color = models.CharField(max_length=50, choices=THEME_CHOICES, default='slide-blue', help_text="Slide background gradient theme")
    banner_image = models.ImageField(upload_to="banners/", blank=True, null=True, help_text="Optional custom background/hero image")
    
    primary_btn_text = models.CharField(max_length=100, default="Explore Store")
    primary_btn_url = models.CharField(max_length=255, default="/products/")
    secondary_btn_text = models.CharField(max_length=100, blank=True, null=True, default="Sell an Item")
    secondary_btn_url = models.CharField(max_length=255, blank=True, null=True, default="/admin/products/product/add/")
    
    order = models.PositiveIntegerField(default=0, help_text="Slide display order (0 comes first)")
    is_active = models.BooleanField(default=True, help_text="Show or hide this slide on homepage")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', '-created_at']
        verbose_name = "Hero Banner Slide"
        verbose_name_plural = "Hero Banner Slides"

    def __str__(self):
        return self.title


class Notification(models.Model):
    NOTIF_TYPES = [
        ('product_listed', 'New Product Listed'),
        ('product_sold', 'Product Sold'),
        ('order_placed', 'Order Placed'),
        ('order_update', 'Order Status Update'),
        ('inquiry', 'New Inquiry'),
        ('message', 'New Message'),
        ('review', 'New Review'),
        ('price_drop', 'Price Drop Alert'),
        ('system', 'System Notification'),
        ('welcome', 'Welcome'),
    ]

    recipient = models.ForeignKey(
        'auth.User', on_delete=models.CASCADE,
        related_name='notifications',
        help_text="The user who receives this notification"
    )
    sender = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='sent_notifications',
        help_text="The user who triggered this notification (optional)"
    )
    notif_type = models.CharField(max_length=30, choices=NOTIF_TYPES, default='system')
    title = models.CharField(max_length=200)
    message = models.TextField(blank=True, default='')
    icon = models.CharField(max_length=50, default='fa-bell', help_text="FontAwesome icon class")
    link = models.CharField(max_length=255, blank=True, default='', help_text="URL to navigate when clicked")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    def __str__(self):
        return f"[{self.get_notif_type_display()}] {self.title}"

    @classmethod
    def notify(cls, recipient, title, message='', notif_type='system', icon='fa-bell', link='', sender=None):
        """Helper to create a notification from anywhere in the codebase."""
        return cls.objects.create(
            recipient=recipient,
            sender=sender,
            notif_type=notif_type,
            title=title,
            message=message,
            icon=icon,
            link=link,
        )

    @classmethod
    def notify_all(cls, title, message='', notif_type='system', icon='fa-bell', link='', exclude_user=None):
        """Send a notification to ALL users (e.g. system announcements)."""
        from django.contrib.auth.models import User
        users = User.objects.filter(is_active=True)
        if exclude_user:
            users = users.exclude(pk=exclude_user.pk)
        notifications = []
        for user in users:
            notifications.append(cls(
                recipient=user,
                notif_type=notif_type,
                title=title,
                message=message,
                icon=icon,
                link=link,
            ))
        return cls.objects.bulk_create(notifications)

