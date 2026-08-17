from datetime import timedelta
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from products.models import Product, Category as ProductCategory, Order, OrderItem, Auction, Bid
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
    
    return render(request, 'home/home1.html', {
        'banners': Banner.objects.filter(is_active=True), 'products': p, 'featured_products': p[:8],
        'categories': ProductCategory.objects.all(), 'blogs': b, 'latest_blogs': b, 'auctions': auctions,
        'total_products': len(p), 'total_categories': ProductCategory.objects.count(), 'total_blogs': len(b)
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
        loc = f"Home: {p.get('home_address', '')}, {p.get('delivery_city', 'Kathmandu')}" if p.get('delivery_type') == 'home_delivery' else f"Campus: {p.get('campus_block', 'Kumari Hall')}"
        order = Order.objects.create(
            user=request.user if request.user.is_authenticated else None,
            buyer_name=p.get('buyer_name', '').strip(), buyer_phone=p.get('buyer_phone', '').strip(),
            buyer_email=p.get('buyer_email', '').strip(), meetup_location=loc,
            meetup_time=p.get('meetup_time', 'Morning'), notes=p.get('notes', ''),
            payment_method=p.get('payment_method', 'esewa_sandbox'), payment_status='Paid (Online Sandbox)', order_status='confirmed'
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
    """
    Extensible Chatbot API with fast answers for basic campus queries and space for Agentic AI integration.
    """
    msg = request.POST.get('message', '').strip() if request.method == 'POST' else request.GET.get('message', '').strip()
    if not msg:
        return JsonResponse({'reply': "Please ask a question about textbooks, auctions, campus pickup blocks, or student blogs."})

    q = msg.lower()
    if any(w in q for w in ['pickup', 'location', 'block', 'where']):
        reply = "<strong>Campus Pickup Blocks:</strong><br>Meet peer sellers at: Kumari Hall, Alumini Block, Skill Block, Nepal Block, Brit House, or Main/Himal Block."
    elif any(w in q for w in ['sell', 'list', 'post', 'upload']):
        reply = "<strong>How to Sell:</strong><br>1. Log in to your student account<br>2. Go to Profile &rarr; Post New Listing<br>3. Upload title, price, category & photo. Admin moderates and publishes it live!"
    elif any(w in q for w in ['auction', 'bid', '24h']):
        reply = "<strong>24-Hour Live Auctions:</strong><br>Student sellers can start 24h auctions on items. Bids are live in real-time, and the highest bidder wins when the timer expires!"
    elif any(w in q for w in ['pay', 'esewa', 'khalti', 'cod', 'cash']):
        reply = "<strong>Payment Options:</strong><br>• Cash on Campus Pickup (COD)<br>• eSewa &amp; Khalti Sandbox for direct home deliveries."
    elif any(w in q for w in ['blog', 'forum', 'question', 'thread']):
        reply = "<strong>Student Blogs &amp; Community:</strong><br>Visit our Blogs section to ask module questions, share notes, or post study guides with peer comments!"
    else:
        # [EXTENSIBLE AGENTIC AI SPACE]
        # Space reserved to call agentic AI API (e.g. Gemini, OpenAI, Claude, Groq):
        # Example: reply = call_ai_agent(msg, user=request.user)
        reply = f"I'm here to help with Islington Marketplace! Ask about textbooks, campus pickup blocks, 24h auctions, or blog discussions."

    return JsonResponse({'reply': reply})

def custom_404(request, exception=None): return render(request, '404.html', status=404)
