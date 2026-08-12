from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Product

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'image_preview')
    search_fields = ('name',)
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.category_image:
            return format_html(
                '<img src="{}" width="60" height="60" style="object-fit:cover; border-radius:6px;" />',
                obj.category_image.url,
            )
        return "No image"

    image_preview.short_description = "Image"

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    exclude = ("created_at",)
    list_display = (
        "name",
        "category",
        "price",
        "stock",
        "status",
        "image_preview",
    )
    search_fields = ("name",)
    list_filter = ("category",)
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("image_preview",)

    def image_preview(self, obj):
        if obj.product_image:
            return format_html(
                '<img src="{}" width="80" height="80" style="object-fit:cover;"'
                " />",
                obj.product_image.url,
            )
        return "No image"

    image_preview.short_description = "Image"