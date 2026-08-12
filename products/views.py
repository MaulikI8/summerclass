from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from .models import Category, Product

def products(request):
    q, cat = request.GET.get('q', '').strip(), request.GET.get('category', '').strip()
    qs = Product.objects.select_related('category').filter(status=True, is_approved=True).order_by('-created_at')
    if q: qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q) | Q(category__name__icontains=q))
    if cat and cat != 'All Categories': qs = qs.filter(category__name__icontains=cat)
    return render(request, 'products/products.html', {
        'products': qs, 'categories': Category.objects.all(),
        'query': q, 'selected_category': cat, 'total_count': qs.count()
    })

def product_detail(request, id):
    p = get_object_or_404(Product, pk=id)
    # Only allow owner or staff to preview unapproved listings
    if not p.is_approved and not (request.user.is_authenticated and (request.user == p.user or request.user.is_staff or request.user.is_superuser)):
        p = get_object_or_404(Product, pk=id, is_approved=True, status=True)
    return render(request, 'products/product_detail.html', {
        'product': p, 'related_products': Product.objects.filter(category=p.category, is_approved=True, status=True).exclude(pk=id)[:4]
    })