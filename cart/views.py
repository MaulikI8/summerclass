from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from products.models import Product
from .models import Cart, CartItem

def _get_or_create_cart(request):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        session_id = request.session.session_key
        if session_id:
            guest_cart = Cart.objects.filter(cart_id=session_id, user__isnull=True).first()
            if guest_cart:
                for item in guest_cart.items.all():
                    existing = cart.items.filter(product=item.product).first()
                    if existing:
                        existing.quantity += item.quantity
                        existing.save()
                    else:
                        item.cart = cart
                        item.save()
                guest_cart.delete()
        return cart
    session_id = request.session.session_key or (request.session.create() or request.session.session_key)
    cart, _ = Cart.objects.get_or_create(cart_id=session_id)
    return cart

def cart_detail(request):
    cart = _get_or_create_cart(request)
    return render(request, 'cart/cart.html', {
        'cart': cart, 'cart_items': cart.items.filter(is_active=True).select_related('product'),
        'total': cart.total_price, 'item_count': cart.total_items_count
    })

from products.models import Product, Variation

def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.user.is_authenticated and product.user == request.user:
        return JsonResponse({'status': 'error', 'message': 'Cannot buy your own listing.'}, status=400) if request.headers.get('x-requested-with') == 'XMLHttpRequest' else redirect('cart:cart_detail')
    
    cart = _get_or_create_cart(request)
    product_variations = []

    if request.method == 'POST':
        for key in request.POST:
            value = request.POST.get(key)
            try:
                var = Variation.objects.filter(product=product, variation_category__iexact=key, variation_value__iexact=value, is_active=True).first()
                if var:
                    product_variations.append(var)
            except Exception:
                pass

    existing_items = CartItem.objects.filter(cart=cart, product=product, is_active=True)
    item = None

    if product_variations and existing_items.exists():
        for ex_item in existing_items:
            existing_vars = list(ex_item.variations.all())
            if set(existing_vars) == set(product_variations):
                item = ex_item
                item.quantity = min(item.quantity + 1, product.stock or 1)
                item.save()
                break

    if item is None:
        item = CartItem.objects.create(cart=cart, product=product, quantity=1)
        if product_variations:
            item.variations.set(product_variations)
            item.save()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success', 'cart_count': cart.total_items_count, 'cart_total': cart.total_price})
    return redirect(request.META.get('HTTP_REFERER', 'cart:cart_detail'))

def remove_from_cart(request, product_id):
    cart = _get_or_create_cart(request)
    item = CartItem.objects.filter(cart=cart, product_id=product_id).first()
    if item:
        if item.quantity > 1: item.quantity -= 1; item.save()
        else: item.delete()
    return JsonResponse({'status': 'success', 'cart_count': cart.total_items_count, 'cart_total': cart.total_price}) if request.headers.get('x-requested-with') == 'XMLHttpRequest' else redirect('cart:cart_detail')

def delete_cart_item(request, product_id):
    CartItem.objects.filter(cart=_get_or_create_cart(request), product_id=product_id).delete()
    return redirect('cart:cart_detail')

def clear_cart(request):
    _get_or_create_cart(request).items.all().delete()
    return redirect('cart:cart_detail')

def api_cart_count(request):
    c = _get_or_create_cart(request)
    return JsonResponse({'count': c.total_items_count, 'total': c.total_price})
