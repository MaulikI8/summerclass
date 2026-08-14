from django.contrib import admin
from .models import Cart, CartItem

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    fields = ('product', 'quantity', 'is_active', 'sub_total_display')
    readonly_fields = ('sub_total_display',)

    def sub_total_display(self, obj):
        return f"Rs. {obj.sub_total:,.2f}"
    sub_total_display.short_description = "Subtotal"

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'cart_id', 'items_count_display', 'total_display', 'date_added', 'updated_at')
    search_fields = ('cart_id', 'user__username', 'user__email')
    list_filter = ('date_added', 'updated_at')
    inlines = [CartItemInline]

    def items_count_display(self, obj):
        return obj.total_items_count
    items_count_display.short_description = "Items"

    def total_display(self, obj):
        return f"Rs. {obj.total_price:,.2f}"
    total_display.short_description = "Total Amount"

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'quantity', 'cart', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('product__name', 'cart__cart_id', 'cart__user__username')
