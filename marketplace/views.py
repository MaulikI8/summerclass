from datetime import timedelta
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from products.models import Product, Category as ProductCategory, Order, OrderItem, Auction, Bid, ItemRequest
from blog.models import Post
from sitesetting.models import Banner, Notification
from utils.email_microservice import EmailMicroservice

def home(request):
    for a in Auction.objects.filter(is_active=True, end_time__lte=timezone.now()):
        a.is_active = False
        a.save()
        if a.highest_bidder:
            a.product.stock = max(0, a.product.stock - 1)
            if a.product.stock == 0: a.product.status = False
            a.product.save()
            o = Order.objects.create(
                user=a.highest_bidder, buyer_name=a.highest_bidder.first_name or a.highest_bidder.username,
                buyer_phone='9800000000', buyer_email=a.highest_bidder.email,
                meetup_location='Block C Library Lobby', meetup_time='Afternoon (1:00 PM - 3:00 PM)',
                notes=f'Won Auction for {a.title}', total_amount=a.current_bid,
                payment_method='auction_bid_won', payment_status='Pending (Collection Payment)', order_status='confirmed'
            )
            OrderItem.objects.create(order=o, product=a.product, product_name=a.product.name, price=a.current_bid, quantity=1)
            EmailMicroservice.send_auction_won_notification(a.highest_bidder, a.product.user, a)
            Notification.notify(a.highest_bidder, f"Won Auction: {a.title}!", f"Winning bid: Rs. {a.current_bid:.2f}", 'auction_won', 'fa-trophy', '/profile/?tab=orders')

    p = list(Product.objects.select_related('category').filter(status=True, is_approved=True).order_by('-created_at'))
    b = list(Post.objects.select_related('category', 'author').filter(status=True).order_by('-created_at')[:3])
    auctions = list(Auction.objects.filter(is_active=True, end_time__gt=timezone.now(), product__is_approved=True).select_related('product', 'highest_bidder', 'product__user').order_by('end_time'))
    wanted = list(ItemRequest.objects.filter(is_fulfilled=False).select_related('user', 'category').order_by('-created_at')[:8])
    
    return render(request, 'home/home1.html', {
        'banners': Banner.objects.filter(is_active=True), 'products': p, 'featured_products': p[:8],
        'categories': ProductCategory.objects.all(), 'blogs': b, 'latest_blogs': b, 'auctions': auctions,
        'wanted_items': wanted, 'total_products': len(p), 'total_categories': ProductCategory.objects.count(), 'total_blogs': len(b)
    })

def start_auction(request, product_id):
    if not request.user.is_authenticated: return redirect('student_login')
    p = get_object_or_404(Product, id=product_id, user=request.user, is_approved=True)
    price = float(request.POST.get('starting_bid') or p.price)
    a, _ = Auction.objects.get_or_create(product=p, defaults={'title': f'24h Auction: {p.name}', 'starting_bid': price, 'current_bid': price, 'end_time': timezone.now() + timedelta(days=1), 'is_active': True})
    a.starting_bid = a.current_bid = price
    a.end_time = timezone.now() + timedelta(days=1)
    a.highest_bidder, a.is_active = None, True
    a.save()
    EmailMicroservice.send_new_auction_broadcast(a, request.build_absolute_uri('/#liveBiddingSection'))
    Notification.notify_all(f'🔥 24h Live Auction: {p.name}', f'Starting at Rs. {price:.2f}!', 'auction_start', 'fa-gavel', '/#liveBiddingSection', exclude_user=request.user)
    messages.success(request, f"24-Hour Live Auction started for {p.name}!")
    return redirect('home')

def accept_auction_bid(request, auction_id):
    if not request.user.is_authenticated: return redirect('student_login')
    a = get_object_or_404(Auction, id=auction_id, is_active=True, highest_bidder__isnull=False)
    if a.product.user != request.user and not request.user.is_superuser: return redirect('home')
    a.is_active = False
    a.save()
    a.product.stock = max(0, a.product.stock - 1)
    if a.product.stock == 0: a.product.status = False
    a.product.save()
    w = a.highest_bidder
    o = Order.objects.create(user=w, buyer_name=w.first_name or w.username, buyer_phone='9800000000', buyer_email=w.email, meetup_location='Block C Library Lobby', meetup_time='Afternoon', total_amount=a.current_bid, payment_method='auction_bid_won', payment_status='Pending', order_status='confirmed')
    OrderItem.objects.create(order=o, product=a.product, product_name=a.product.name, price=a.current_bid, quantity=1)
    EmailMicroservice.send_auction_won_notification(w, request.user, a)
    Notification.notify(w, f"Bid Accepted for {a.title}!", f"Price: Rs. {a.current_bid:.2f}", 'auction_won', 'fa-trophy', '/profile/?tab=orders')
    messages.success(request, f"Accepted bid of Rs. {a.current_bid:.2f} from {w.username}.")
    return redirect('home')

def place_bid(request, auction_id):
    if not request.user.is_authenticated: return redirect('student_login')
    a = get_object_or_404(Auction, id=auction_id, is_active=True)
    if a.product.user == request.user:
        messages.error(request, "Cannot bid on your own listing.")
        return redirect('home')
    if request.method == 'POST':
        amt = float(request.POST.get('bid_amount', 0))
        if amt <= a.current_bid:
            messages.error(request, f"Bid must exceed current Rs. {a.current_bid:.2f}")
            return redirect('home')
        old_bidder = a.highest_bidder
        Bid.objects.create(auction=a, user=request.user, amount=amt)
        a.current_bid, a.highest_bidder = amt, request.user
        a.save()
        if old_bidder and old_bidder != request.user:
            EmailMicroservice.send_outbid_notification(old_bidder, a, amt, request.build_absolute_uri('/#liveBiddingSection'))
            Notification.notify(old_bidder, f"Outbid on {a.product.name}!", f"New highest bid: Rs. {amt:.2f}.", 'auction_outbid', 'fa-arrow-up', '/#liveBiddingSection')
        messages.success(request, f"Highest bid of Rs. {amt:.2f} placed!")
    return redirect('home')

def checkout(request):
    from cart.views import _get_or_create_cart
    cart = _get_or_create_cart(request)
    cart_items = cart.items.filter(is_active=True).select_related('product', 'product__user')
    if not cart_items.exists(): return redirect('products')

    if request.method == 'POST':
        p = request.POST
        loc = f"Home (Kathmandu): {p.get('home_address', '')}" if p.get('delivery_type') == 'home_delivery' else f"Campus: {p.get('campus_block', 'Kumari Hall')}"
        pm = p.get('payment_method', 'esewa_sandbox')
        if pm not in ['esewa_sandbox', 'khalti_sandbox']:
            pm = 'esewa_sandbox'
        order = Order.objects.create(
            user=request.user if request.user.is_authenticated else None,
            buyer_name=p.get('buyer_name', '').strip(), buyer_phone=p.get('buyer_phone', '').strip(),
            buyer_email=p.get('buyer_email', '').strip(), meetup_location=loc,
            meetup_time=p.get('meetup_time', 'Morning'), notes=p.get('notes', ''),
            payment_method=pm, payment_status='Paid (Online Sandbox)', order_status='confirmed'
        )
        total = 0.0
        site_url = request.build_absolute_uri('/')[:-1]
        for item in cart_items:
            prod, pr, qty = item.product, float(item.product.price if item.product else 0), item.quantity
            OrderItem.objects.create(order=order, product=prod, product_name=prod.name if prod else 'Item', price=pr, quantity=qty)
            total += pr * qty
            if prod and prod.user and prod.user != request.user:
                Notification.notify(prod.user, f'New Order #{order.id} for {prod.name}!', f'{order.buyer_name} ordered {qty}x.', 'order_placed', 'fa-receipt', '/profile/?tab=orders')
                EmailMicroservice.send_seller_new_order_email(prod.user, prod, order, qty, site_url=site_url)
        order.total_amount = total
        order.save()
        cart_items.delete()
        EmailMicroservice.send_order_confirmation_email(order, site_url=site_url)
        return redirect('order_success', order_id=order.id)

    return render(request, 'profile/checkout.html', {'cart': cart, 'cart_items': cart_items, 'total': cart.total_price, 'item_count': cart.total_items_count})

def order_success(request, order_id):
    return render(request, 'profile/order_success.html', {'order': get_object_or_404(Order, id=order_id)})

def api_chatbot(request):
    from utils.agentic_bot import AgenticCommerceBot
    import json
    if request.method == 'POST':
        if request.content_type == 'application/json':
            try:
                body = json.loads(request.body.decode('utf-8'))
                msg = body.get('message', '').strip()
            except Exception:
                msg = ''
        else:
            msg = request.POST.get('message', '').strip()
    else:
        msg = request.GET.get('message', '').strip()

    if not msg:
        return JsonResponse({'reply': "Hi! I am your AI Shopping Assistant. Ask me to find products (e.g., 'Find tech under Rs. 1500'), manage your cart, or check you out!", 'products': [], 'action_type': 'general', 'cart_data': {}})

    result = AgenticCommerceBot.process_query(msg, request)
    return JsonResponse(result)

def custom_404(request, exception=None): return render(request, '404.html', status=404)
