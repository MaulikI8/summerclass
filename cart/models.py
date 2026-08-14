from django.db import models
from django.contrib.auth.models import User
from products.models import Product

class Cart(models.Model):
    cart_id = models.CharField(max_length=255, blank=True, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='user_carts')
    date_added = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_added']
        verbose_name = 'Shopping Cart'
        verbose_name_plural = 'Shopping Carts'

    def __str__(self):
        if self.user:
            return f"Cart for {self.user.username}"
        return f"Guest Cart: {self.cart_id}"

    @property
    def total_price(self):
        return sum(item.sub_total for item in self.items.filter(is_active=True))

    @property
    def total_items_count(self):
        return sum(item.quantity for item in self.items.filter(is_active=True))


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='cart_items')
    quantity = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Cart Item'
        verbose_name_plural = 'Cart Items'

    @property
    def sub_total(self):
        return (self.product.price or 0.0) * self.quantity

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"
