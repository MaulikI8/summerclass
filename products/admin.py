from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Product, Order, OrderItem, Auction, Bid

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'img_preview')
    def img_preview(self, o): return format_html('<img src="{}" width="50" height="50" style="object-fit:cover;border-radius:4px;" />', o.category_image.url) if o.category_image else "—"

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'stock', 'status', 'img_preview')
    search_fields = ('name',)
    list_filter = ('category', 'status')
    prepopulated_fields = {'slug': ('name',)}
    def img_preview(self, o): return format_html('<img src="{}" width="50" height="50" style="object-fit:cover;border-radius:4px;" />', o.product_image.url) if o.product_image else "—"

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'buyer_name', 'buyer_phone', 'total_amount', 'payment_method', 'order_status', 'created_at')
    list_filter = ('payment_method', 'order_status', 'created_at')
    search_fields = ('buyer_name', 'buyer_phone', 'buyer_email')
    inlines = [OrderItemInline]

class BidInline(admin.TabularInline):
    model = Bid
    extra = 0
    readonly_fields = ('user', 'amount', 'created_at')

@admin.register(Auction)
class AuctionAdmin(admin.ModelAdmin):
    list_display = ('title', 'product', 'current_bid', 'starting_bid', 'highest_bidder', 'end_time', 'is_active')
    list_filter = ('is_active', 'end_time')
    search_fields = ('title', 'product__name')
    inlines = [BidInline]