from django.db import models
from django.contrib.auth.models import User

class SiteSetting(models.Model):
    site_title, meta_description, meta_keywords = models.CharField(max_length=200, default="MarketPlace"), models.TextField(blank=True, null=True), models.CharField(max_length=255, blank=True, null=True)
    logo, favicon, copyright = models.ImageField(upload_to="photos/logos/", blank=True, null=True), models.ImageField(upload_to="photos/favicons/", blank=True, null=True), models.CharField(max_length=200, blank=True, null=True)
    def __str__(self): return "Site Setting"

class Banner(models.Model):
    featured_product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        limit_choices_to={'is_approved': True},
        help_text="Select an existing approved posting from the marketplace to showcase in this banner.",
        related_name="banners"
    )
    title = models.CharField(max_length=200, blank=True, help_text="Optional custom title. Leave blank to auto-use product name.")
    subtitle = models.TextField(blank=True, help_text="Optional custom description. Leave blank to auto-use product description.")
    badge_text = models.CharField(max_length=100, default="Featured Campus Item", blank=True)
    badge_icon = models.CharField(max_length=50, default="fa-star", blank=True)
    theme_color = models.CharField(max_length=50, default='slide-blue', choices=[('slide-blue', 'Blue Gradient'), ('slide-green', 'Emerald Green'), ('slide-purple', 'Purple Accent')])
    banner_image = models.ImageField(upload_to="banners/", blank=True, null=True, help_text="Optional custom banner image. If empty, uses product photo.")
    primary_btn_text = models.CharField(max_length=100, default="View Listing", blank=True)
    primary_btn_url = models.CharField(max_length=255, default="/products/", blank=True)
    secondary_btn_text = models.CharField(max_length=100, blank=True, null=True, default="Explore Store")
    secondary_btn_url = models.CharField(max_length=255, blank=True, null=True, default="/products/")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', '-created_at']

    def save(self, *args, **kwargs):
        try:
            if self.featured_product:
                if not self.title:
                    self.title = self.featured_product.name or ''
                if not self.subtitle:
                    desc = self.featured_product.description or "Verified student listing available for campus pickup."
                    self.subtitle = str(desc)[:200]
                if not self.primary_btn_url or self.primary_btn_url == "/products/":
                    self.primary_btn_url = f"/products/{self.featured_product.id}/"
                if not self.badge_text or self.badge_text == "Featured Campus Item":
                    price = f"{self.featured_product.price:.2f}" if getattr(self.featured_product, 'price', None) is not None else "0.00"
                    self.badge_text = f"Featured • Rs. {price}"
                if not self.banner_image and getattr(self.featured_product, 'product_image', None):
                    try:
                        self.banner_image = self.featured_product.product_image
                    except Exception:
                        pass
        except Exception:
            pass
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title or (self.featured_product.name if (self.featured_product and self.featured_product.name) else f"Banner #{self.pk or 'New'}")

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

class EmailOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otp_codes')
    otp_code = models.CharField(max_length=6, db_index=True)
    purpose = models.CharField(max_length=50, default='registration')
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Email OTP Verification'
        verbose_name_plural = 'Email OTP Verifications'

    def is_valid(self):
        import datetime
        from django.utils import timezone
        return not self.is_used and (timezone.now() - self.created_at) < datetime.timedelta(minutes=10)

    def __str__(self):
        return f"OTP {self.otp_code} for {self.user.username} ({'Used' if self.is_used else 'Active'})"

