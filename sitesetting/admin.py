from django.contrib import admin
from django.utils.html import format_html
from django import forms
from .models import SiteSetting, Banner
from products.models import Product

@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    has_add_permission = lambda s, r: not SiteSetting.objects.exists()

class BannerAdminForm(forms.ModelForm):
    class Meta:
        model = Banner
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'featured_product' in self.fields:
            try:
                self.fields['featured_product'].queryset = Product.objects.filter(is_approved=True).select_related('category').order_by('-created_at')
                def make_label(obj):
                    cat_name = obj.category.name if getattr(obj, 'category', None) else 'General'
                    price = f"{obj.price:.2f}" if getattr(obj, 'price', None) is not None else "0.00"
                    return f"{obj.name or 'Item'} — Rs. {price} ({cat_name})"
                self.fields['featured_product'].label_from_instance = make_label
            except Exception:
                pass

@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    form = BannerAdminForm
    list_display = ('title', 'featured_item_preview', 'badge_text', 'theme_color', 'order', 'is_active', 'image_preview')
    list_filter = ('theme_color', 'is_active')
    list_editable = ('order', 'is_active')
    search_fields = ('title', 'subtitle', 'featured_product__name')
    fieldsets = (
        ("Select from Existing Approved Postings", {'fields': ('featured_product',)}),
        ("Banner Styling & Theme", {'fields': ('theme_color', 'badge_text', 'badge_icon', 'order', 'is_active')}),
        ("Custom Overrides (Optional)", {'fields': ('title', 'subtitle', 'banner_image', 'primary_btn_text', 'primary_btn_url', 'secondary_btn_text', 'secondary_btn_url'), 'classes': ('collapse',)}),
    )

    def featured_item_preview(self, o):
        try:
            if o.featured_product:
                name = o.featured_product.name or "Item"
                price = f"{o.featured_product.price:.2f}" if getattr(o.featured_product, 'price', None) is not None else "0.00"
                return format_html('<strong>{}</strong> (Rs. {})', name, price)
        except Exception:
            pass
        return "-"

    featured_item_preview.short_description = "Selected Posting"

    def image_preview(self, o):
        try:
            img_url = None
            if o.banner_image and hasattr(o.banner_image, 'url'):
                img_url = o.banner_image.url
            elif o.featured_product and o.featured_product.product_image and hasattr(o.featured_product.product_image, 'url'):
                img_url = o.featured_product.product_image.url
            if img_url:
                return format_html('<img src="{}" height="38" style="border-radius:6px;object-fit:cover;" />', img_url)
        except Exception:
            pass
        return "-"
    image_preview.short_description = "Banner Preview"
