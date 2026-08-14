from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from products.models import Product
from .models import Cart, CartItem

def _get_cart_id(request):
    cart_id = request.session.session_key
    if not cart_id:
        request.session.create()
        cart_id = request.session.session_key
    return cart_id

def _get_or_create_cart(request):
    if request.user.is_authenticated:
        # Check if user has an existing cart
        cart, created = Cart.objects.get_or_create(user=request.user)
        # Migrate guest cart items if any existed before logging in
        session_cart_id = request.session.session_key
        if session_cart_id:
            guest_cart = Cart.objects.filter(cart_id=session_cart_id, user__isnull=True).first()
            if guest_cart:
                for g_item in guest_cart.items.all():
                    existing = cart.items.filter(product=g_item.product).first()
                    if existing:
                        existing.quantity += g_item.quantity
                        existing.save()
                    else:
                        g_item.cart = cart
                        g_item.save()
                guest_cart.delete()
        return cart
    else:
        cart_id = _get_cart_id(request)
        cart, created = Cart.objects.get_or_create(cart_id=cart_id)
        return cart

def cart_detail(request):
    cart = _get_or_create_cart(request)
    cart_items = cart.items.filter(is_active=True).select_related('product', 'product__category', 'product__user')
    total = cart.total_price
    item_count = cart.total_items_count

    context = {
        'cart': cart,
        'cart_items': cart_items,
        'total': total,
        'item_count': item_count,
    }
    return render(request, 'cart/cart.html', context)

def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    # Prevent seller from buying their own product
    if request.user.is_authenticated and product.user == request.user:
        msg = f"You are the seller of '{product.name}'. You cannot add your own product to the cart."
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('format') == 'json':
            return JsonResponse({'status': 'error', 'message': msg}, status=400)
        messages.error(request, msg)
        return redirect(request.META.get('HTTP_REFERER', 'cart:cart_detail'))

    if product.stock <= 0:
        msg = f"'{product.name}' is currently out of stock."
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('format') == 'json':
            return JsonResponse({'status': 'error', 'message': msg}, status=400)
        messages.error(request, msg)
        return redirect(request.META.get('HTTP_REFERER', 'cart:cart_detail'))

    cart = _get_or_create_cart(request)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)

    if not created:
        if cart_item.quantity < product.stock:
            cart_item.quantity += 1
            cart_item.save()
        else:
            msg = f"Maximum available stock for '{product.name}' reached."
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('format') == 'json':
                return JsonResponse({'status': 'warning', 'message': msg, 'cart_count': cart.total_items_count}, status=200)
            messages.warning(request, msg)
            return redirect('cart:cart_detail')
    else:
        cart_item.quantity = 1
        cart_item.save()

    msg = f"Added '{product.name}' to your shopping bag."
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('format') == 'json':
        return JsonResponse({
            'status': 'success',
            'message': msg,
            'cart_count': cart.total_items_count,
            'cart_total': cart.total_price,
            'item_quantity': cart_item.quantity
        })

    messages.success(request, msg)
    return redirect(request.META.get('HTTP_REFERER', 'cart:cart_detail'))

def remove_from_cart(request, product_id):
    cart = _get_or_create_cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart_item = CartItem.objects.filter(cart=cart, product=product).first()

    if cart_item:
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        else:
            cart_item.delete()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('format') == 'json':
        return JsonResponse({
            'status': 'success',
            'cart_count': cart.total_items_count,
            'cart_total': cart.total_price
        })

    return redirect('cart:cart_detail')

def delete_cart_item(request, product_id):
    cart = _get_or_create_cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart_item = CartItem.objects.filter(cart=cart, product=product).first()

    if cart_item:
        cart_item.delete()
        messages.info(request, f"Removed '{product.name}' from your shopping bag.")

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('format') == 'json':
        return JsonResponse({
            'status': 'success',
            'cart_count': cart.total_items_count,
            'cart_total': cart.total_price
        })

    return redirect('cart:cart_detail')

def clear_cart(request):
    cart = _get_or_create_cart(request)
    cart.items.all().delete()
    messages.info(request, "Your shopping bag has been cleared.")

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('format') == 'json':
        return JsonResponse({'status': 'success', 'cart_count': 0, 'cart_total': 0.0})

    return redirect('cart:cart_detail')

def api_cart_count(request):
    cart = _get_or_create_cart(request)
    return JsonResponse({
        'count': cart.total_items_count,
        'total': cart.total_price
    })
