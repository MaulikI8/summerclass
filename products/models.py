import time
from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.utils import timezone

class Category(models.Model):
    name = models.CharField(max_length=225)
    category_image = models.ImageField(upload_to='categories/', blank=True, null=True)
    class Meta: verbose_name_plural = 'Categories'
    def __str__(self): return self.name

class Product(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='products')
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=150, unique=True, blank=True, null=True)
    price = models.FloatField()
    description = models.TextField()
    stock = models.IntegerField(default=1)
    status = models.BooleanField(default=True, help_text="Public visibility on store")
    is_approved = models.BooleanField(default=True, verbose_name="Approved by Admin", help_text="Designates whether this listing is approved by admin.")
    rejection_reason = models.TextField(blank=True, null=True, help_text="Optional feedback if rejected by admin.")
    product_image = models.ImageField(upload_to='products/', blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug: self.slug = f"{slugify(self.name)}-{int(time.time())}"
        super().save(*args, **kwargs)

    def __str__(self): return self.name

class PendingProductReview(Product):
    class Meta:
        proxy = True
        verbose_name = "Pending Product Review"
        verbose_name_plural = "Pending Product Reviews (Moderation Hub)"

class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    buyer_name = models.CharField(max_length=150)
    buyer_phone = models.CharField(max_length=50)
    buyer_email = models.EmailField(blank=True, null=True)
    meetup_location = models.CharField(max_length=150, default='Block C Library Lobby')
    meetup_time = models.CharField(max_length=100, default='Morning (10:00 AM - 12:00 PM)')
    notes = models.TextField(blank=True, default='')
    total_amount = models.FloatField(default=0.0)
    payment_method = models.CharField(max_length=50, default='esewa_sandbox')
    payment_status = models.CharField(max_length=50, default='Paid (Online Sandbox)')
    order_status = models.CharField(max_length=30, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['-created_at']
    def __str__(self): return f"Order #{self.id} - {self.buyer_name} (Rs. {self.total_amount:.2f})"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    product_name = models.CharField(max_length=150)
    price = models.FloatField()
    quantity = models.PositiveIntegerField(default=1)
    def __str__(self): return f"{self.quantity}x {self.product_name}"

class Auction(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='auction')
    title = models.CharField(max_length=200)
    starting_bid = models.FloatField(default=100.0)
    current_bid = models.FloatField(default=100.0)
    highest_bidder = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='won_bids')
    end_time = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['end_time']
    @property
    def bids_count(self): return self.bids.count()
    def __str__(self): return f"Auction: {self.title} (Current: Rs. {self.current_bid:.2f})"

class Bid(models.Model):
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE, related_name='bids')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='placed_bids')
    amount = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['-created_at']
    def __str__(self): return f"{self.user.username} - Rs. {self.amount:.2f}"
