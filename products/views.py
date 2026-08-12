from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from .models import Category, Product

def products(request):
    product_list = Product.objects.select_related('category').all().order_by('-created_at')
    categories = Category.objects.all()
    
    q = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    
    if q:
        product_list = product_list.filter(
            Q(name__icontains=q) | 
            Q(description__icontains=q) |
            Q(category__name__icontains=q)
        )
        
    if category and category != 'All Categories':
        product_list = product_list.filter(category__name__icontains=category)
        
    context = {
        'products': product_list,
        'categories': categories,
        'query': q,
        'selected_category': category,
        'total_count': product_list.count(),
    }
    return render(request, 'products/products.html', context)

def product_detail(request, id):
    product = get_object_or_404(Product, pk=id)
    related_products = Product.objects.filter(category=product.category).exclude(pk=id)[:4]
    return render(request, 'products/product_detail.html', {
        'product': product,
        'related_products': related_products,
    })