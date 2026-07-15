from django.contrib import admin
from .models import Category, Product

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id','name')
admin.site.register(Category,CategoryAdmin)

class ProductAdmin(admin.ModelAdmin):
    exclude=('created_at',)
    list_display=('id','name','price','stock','category','status')



admin.site.register(Product,ProductAdmin)

