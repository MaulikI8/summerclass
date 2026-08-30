import time
from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.utils import timezone

class Category(models.Model):
    name = models.CharField(max_length=225)
    category_image = models.ImageField(upload_to='categories/', blank=True, null=True)
    class Meta: verbose_name_plural = 'Categories'
    def get_url(self):
        return f"/products/?category={self.name}"
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

    def get_url(self):
        from django.urls import reverse
        return reverse('product_detail', args=[self.id])

    @property
    def average_rating(self):
        reviews = self.reviews.filter(status=True)
        if not reviews.exists():
            return 0.0
        total = sum(r.rating for r in reviews)
        return round(total / reviews.count(), 1)

    @property
    def count_reviews(self):
        return self.reviews.filter(status=True).count()

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

class TradeOffer(models.Model):
    OFFER_TYPES = [('price', 'Price Offer'), ('trade', 'Item Trade / Swap')]
    STATUS_CHOICES = [('pending', 'Pending'), ('accepted', 'Accepted'), ('declined', 'Declined')]
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='offers')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_offers')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_offers')
    offer_type = models.CharField(max_length=10, choices=OFFER_TYPES, default='price')
    offered_price = models.FloatField(blank=True, null=True)
    trade_item_desc = models.TextField(blank=True, help_text="Item offered in exchange or notes")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['-created_at']
    def __str__(self): return f"Offer from {self.sender.username} on {self.product.name} ({self.status})"

class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlisted_by')
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ('user', 'product')
        ordering = ['-created_at']
    def __str__(self): return f"{self.user.username} saved {self.product.name}"

class ItemRequest(models.Model):
    URGENCY_CHOICES = [('today', 'Needed Today'), ('week', 'Needed This Week'), ('flexible', 'Flexible')]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='item_requests')
    title = models.CharField(max_length=150)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    budget = models.FloatField(default=0.0)
    urgency = models.CharField(max_length=20, choices=URGENCY_CHOICES, default='today')
    preferred_location = models.CharField(max_length=100, default='Kumari Hall')
    contact_phone = models.CharField(max_length=30, blank=True)
    description = models.TextField(blank=True)
    is_fulfilled = models.BooleanField(default=False)
    fulfilled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='fulfilled_requests')
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['-created_at']
    def __str__(self): return f"Wanted: {self.title} by {self.user.username}"

class SearchHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='search_histories')
    session_key = models.CharField(max_length=100, null=True, blank=True)
    query = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Search History'

    def __str__(self):
        user_display = self.user.username if self.user else (self.session_key or 'Anonymous')
        return f"'{self.query}' by {user_display}"


class ProductView(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='product_views')
    session_key = models.CharField(max_length=100, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='views')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Product View'
        verbose_name_plural = 'Product Views'

    def __str__(self):
        user_disp = self.user.username if self.user else (self.session_key or 'Anonymous')
        return f"Viewed {self.product.name} by {user_disp}"


class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField(default=5)
    comment = models.TextField(blank=True)
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')
        ordering = ['-created_at']

    def __str__(self):
        return f"Review ({self.rating}★) by {self.user.username} on {self.product.name}"


class VariationManager(models.Manager):
    def colors(self):
        return super().filter(variation_category='color', is_active=True)

    def sizes(self):
        return super().filter(variation_category='size', is_active=True)

    def conditions(self):
        return super().filter(variation_category='condition', is_active=True)


VARIATION_CATEGORY_CHOICES = (
    ('size', 'Size'),
    ('color', 'Color'),
    ('condition', 'Condition'),
    ('edition', 'Edition / Version'),
)

class Variation(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variations')
    variation_category = models.CharField(max_length=100, choices=VARIATION_CATEGORY_CHOICES)
    variation_value = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = VariationManager()

    class Meta:
        ordering = ['variation_category', 'variation_value']

    def __str__(self):
        return f"{self.product.name} - {self.get_variation_category_display()}: {self.variation_value}"




