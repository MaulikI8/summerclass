from django.contrib import admin, messages
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import path
from django.shortcuts import redirect, get_object_or_404
from .models import Category, Product, PendingProductReview, Order, OrderItem, Auction, Bid
from sitesetting.models import Notification
from utils.email_microservice import EmailMicroservice

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'img_preview')
    def img_preview(self, o): 
        try:
            if o.category_image:
                return format_html('<img src="{}" width="50" height="50" style="object-fit:cover;border-radius:6px;" />', o.category_image.url)
        except Exception:
            pass
        return mark_safe('<span style="color:#94a3b8;font-size:11px;">—</span>')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('img_preview', 'name', 'user_seller', 'category', 'price', 'stock', 'approval_badge', 'status', 'created_at')
    search_fields = ('name', 'description', 'user__username', 'user__email')
    list_filter = ('is_approved', 'status', 'category', 'created_at')
    prepopulated_fields = {'slug': ('name',)}
    actions = ['approve_selected_products', 'unapprove_selected_products']

    def user_seller(self, o):
        return o.user.username if o.user else "Admin (Store)"
    user_seller.short_description = "Seller"

    def approval_badge(self, o):
        if o.is_approved:
            return mark_safe('<span style="background:#dcfce7;color:#15803d;padding:4px 10px;border-radius:12px;font-weight:bold;font-size:11px;">✔ Approved</span>')
        return mark_safe('<span style="background:#fef3c7;color:#b45309;padding:4px 10px;border-radius:12px;font-weight:bold;font-size:11px;">⏳ Pending Review</span>')
    approval_badge.short_description = "Review Status"

    def img_preview(self, o): 
        try:
            if o.product_image:
                return format_html('<img src="{}" width="48" height="48" style="object-fit:cover;border-radius:6px;" />', o.product_image.url)
        except Exception:
            pass
        return mark_safe('<span style="color:#94a3b8;font-size:11px;">No photo</span>')
    img_preview.short_description = "Photo"

    @admin.action(description="Approve selected products (Publish to Store)")
    def approve_selected_products(self, request, queryset):
        count = queryset.update(is_approved=True, status=True)
        site_url = request.build_absolute_uri('/')[:-1]
        for p in queryset:
            if p.user:
                EmailMicroservice.send_product_approved_email(p.user, p, site_url=site_url)
                Notification.notify(p.user, f"Listing Approved: {p.name}", f"Your listing '{p.name}' is now live on the marketplace!", 'product_approved', 'fa-check-circle', f'/products/{p.id}/')
        self.message_user(request, f"{count} products successfully approved and published to the store. (Emails sent)", messages.SUCCESS)

    @admin.action(description="Unapprove selected products (Hide from Store)")
    def unapprove_selected_products(self, request, queryset):
        count = queryset.update(is_approved=False, status=False)
        self.message_user(request, f"{count} products unapproved.", messages.WARNING)

    def save_model(self, request, obj, form, change):
        if change:
            try:
                old = Product.objects.get(pk=obj.pk)
                if not old.is_approved and obj.is_approved:
                    obj.status = True
                    if obj.user:
                        site_url = request.build_absolute_uri('/')[:-1]
                        EmailMicroservice.send_product_approved_email(obj.user, obj, site_url=site_url)
                        Notification.notify(obj.user, f"Listing Approved: {obj.name}", f"Your listing '{obj.name}' is now live!", 'product_approved', 'fa-check-circle', f'/products/{obj.id}/')
            except Exception:
                pass
        super().save_model(request, obj, form, change)


@admin.register(PendingProductReview)
class PendingProductReviewAdmin(admin.ModelAdmin):
    """
    Dedicated Moderation Section for Admins to Review & Approve Student Listings.
    """
    list_display = ('img_preview', 'name', 'user_seller', 'category', 'price', 'stock', 'created_at', 'review_actions')
    list_filter = ('category', 'created_at')
    search_fields = ('name', 'description', 'user__username', 'user__email')
    actions = ['approve_selected_reviews', 'reject_selected_reviews']

    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_approved=False)

    def user_seller(self, o):
        return format_html('<b>{}</b><br><small style="color:#64748b;">{}</small>', o.user.username if o.user else "Admin", o.user.email if o.user else "")
    user_seller.short_description = "Student Seller"

    def img_preview(self, o): 
        try:
            if o.product_image:
                return format_html('<img src="{}" width="52" height="52" style="object-fit:cover;border-radius:8px;border:1px solid #e2e8f0;" />', o.product_image.url)
        except Exception:
            pass
        return mark_safe('<span style="color:#94a3b8;font-size:11px;">No photo</span>')
    img_preview.short_description = "Photo"

    def review_actions(self, o):
        return format_html(
            '<div style="display:flex;gap:6px;">'
            '<a class="button" style="background:#16a34a;color:#fff;font-weight:bold;padding:5px 12px;border-radius:4px;text-decoration:none;" href="approve/{}/">✔ Approve</a>'
            '<a class="button" style="background:#dc2626;color:#fff;font-weight:bold;padding:5px 12px;border-radius:4px;text-decoration:none;" href="reject/{}/" onclick="return confirm(\'Reject listing for {}\');">✖ Reject</a>'
            '</div>',
            o.id, o.id, o.name
        )
    review_actions.short_description = "Moderation Actions"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('approve/<int:product_id>/', self.admin_site.admin_view(self.approve_single), name='product_review_approve'),
            path('reject/<int:product_id>/', self.admin_site.admin_view(self.reject_single), name='product_review_reject'),
        ]
        return custom_urls + urls

    def approve_single(self, request, product_id):
        p = get_object_or_404(Product, id=product_id)
        p.is_approved = True
        p.status = True
        p.save()
        if p.user:
            site_url = request.build_absolute_uri('/')[:-1]
            EmailMicroservice.send_product_approved_email(p.user, p, site_url=site_url)
            Notification.notify(p.user, f"Listing Approved: {p.name}", f"Your listing '{p.name}' has been approved by admin and is now live on the marketplace.", 'product_approved', 'fa-check-circle', f'/products/{p.id}/')
        self.message_user(request, f"Listing '{p.name}' approved and published. (Email sent to student)", messages.SUCCESS)
        return redirect('../../')

    def reject_single(self, request, product_id):
        p = get_object_or_404(Product, id=product_id)
        p.is_approved = False
        p.status = False
        p.save()
        if p.user:
            EmailMicroservice.send_product_rejected_email(p.user, p, reason="Item did not meet marketplace listing guidelines.")
            Notification.notify(p.user, f"Listing Not Approved: {p.name}", f"Your listing '{p.name}' was not approved by college admin. Please verify details.", 'product_rejected', 'fa-times-circle', '/profile/?tab=products')
        self.message_user(request, f"Listing '{p.name}' rejected. (Email notice sent to student)", messages.WARNING)
        return redirect('../../')

    @admin.action(description="Approve all selected listings")
    def approve_selected_reviews(self, request, queryset):
        count = 0
        site_url = request.build_absolute_uri('/')[:-1]
        for p in queryset:
            p.is_approved = True
            p.status = True
            p.save()
            if p.user:
                EmailMicroservice.send_product_approved_email(p.user, p, site_url=site_url)
                Notification.notify(p.user, f"Listing Approved: {p.name}", f"Your listing '{p.name}' has been approved by admin.", 'product_approved', 'fa-check-circle', f'/products/{p.id}/')
            count += 1
        self.message_user(request, f"{count} listings approved and published to the store.", messages.SUCCESS)

    @admin.action(description="Reject all selected listings")
    def reject_selected_reviews(self, request, queryset):
        for p in queryset:
            if p.user:
                EmailMicroservice.send_product_rejected_email(p.user, p)
        count = queryset.update(is_approved=False, status=False)
        self.message_user(request, f"{count} listings rejected.", messages.WARNING)


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