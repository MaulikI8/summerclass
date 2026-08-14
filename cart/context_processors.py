from .models import Cart, CartItem

def _get_or_create_cart_id(request):
    cart_id = request.session.session_key
    if not cart_id:
        request.session.create()
        cart_id = request.session.session_key
    return cart_id

def cart_counter(request):
    cart_count = 0
    cart_total = 0.0
    try:
        if request.user.is_authenticated:
            cart = Cart.objects.filter(user=request.user).first()
        else:
            cart_id = _get_or_create_cart_id(request)
            cart = Cart.objects.filter(cart_id=cart_id).first()

        if cart:
            cart_count = cart.total_items_count
            cart_total = cart.total_price
    except Exception:
        cart_count = 0
        cart_total = 0.0

    return {
        'cart_count': cart_count,
        'cart_total': cart_total,
    }
