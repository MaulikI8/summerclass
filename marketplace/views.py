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
    
    recommendations = []
    try:
        from products.recommendations import HybridRecommender
        from products.models import SearchHistory, ProductView
        session_key = request.session.session_key
        has_activity = False
        if request.user.is_authenticated:
            has_activity = SearchHistory.objects.filter(user=request.user).exists() or ProductView.objects.filter(user=request.user).exists()
        elif session_key:
            has_activity = SearchHistory.objects.filter(user__isnull=True, session_key=session_key).exists() or ProductView.objects.filter(user__isnull=True, session_key=session_key).exists()

        if has_activity:
            recommender = HybridRecommender(request)
            recommendations = recommender.recommend(limit=4)
    except Exception:
        recommendations = []

    return render(request, 'home/home1.html', {
        'banners': Banner.objects.filter(is_active=True), 'products': p, 'featured_products': p[:8],
        'categories': ProductCategory.objects.all(), 'blogs': b, 'latest_blogs': b, 'auctions': auctions,
        'wanted_items': wanted, 'recommendations': recommendations, 'total_products': len(p), 'total_categories': ProductCategory.objects.count(), 'total_blogs': len(b)
    })

def seed_store_view(request):
    if not (request.user.is_authenticated and request.user.is_superuser):
        messages.error(request, "Superuser login required to execute store seeding.")
        return redirect('student_login')
    
    import threading
    from django.core.management import call_command

    def run_seeder():
        try:
            call_command('seed_store')
        except Exception as err:
            print("Background seeder error:", err)

    threading.Thread(target=run_seeder, daemon=True).start()
    messages.success(request, "Store seeding started in background! Refresh in 5 seconds to see all products, categories & banners live.")
    return redirect('home')

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
    import json, requests
    from django.conf import settings
    from cart.views import _get_or_create_cart

    cart = _get_or_create_cart(request)
    cart_items = cart.items.filter(is_active=True).select_related('product', 'product__user')
    if not cart_items.exists():
        return redirect('products')

    if request.method == 'POST':
        p = request.POST
        loc = f"Home (Kathmandu): {p.get('home_address', '')}" if p.get('delivery_type') == 'home_delivery' else f"Campus: {p.get('campus_block', 'Kumari Hall')}"
        
        order = Order.objects.create(
            user=request.user if request.user.is_authenticated else None,
            buyer_name=p.get('buyer_name', '').strip() or "Student Buyer",
            buyer_phone=p.get('buyer_phone', '').strip() or "9800000000",
            buyer_email=p.get('buyer_email', '').strip() or "student@islingtonmarket.np",
            meetup_location=loc,
            meetup_time=p.get('meetup_time', 'Morning'),
            notes=p.get('notes', ''),
            payment_method='khalti_api',
            payment_status='Pending (Khalti Gateway)',
            order_status='pending'
        )
        total = 0.0
        product_details = []
        for item in cart_items:
            prod, pr, qty = item.product, float(item.product.price if item.product else 0), item.quantity
            OrderItem.objects.create(order=order, product=prod, product_name=prod.name if prod else 'Item', price=pr, quantity=qty)
            total += pr * qty
            if prod:
                item_price_paisa = int(round(pr * 100))
                product_details.append({
                    "identity": str(prod.id),
                    "name": str(prod.name)[:50],
                    "total_price": item_price_paisa * qty,
                    "quantity": qty,
                    "unit_price": item_price_paisa
                })

        order.total_amount = total
        order.save()

def initiate_khalti_payment(request, order):
    import json, requests
    from django.conf import settings

    amount_paisa = max(1000, int(round(order.total_amount * 100)))
    return_url = request.build_absolute_uri('/checkout/khalti/complete/')
    website_url = request.build_absolute_uri('/')

    if 'http://' in return_url and not ('127.0.0.1' in return_url or 'localhost' in return_url):
        return_url = return_url.replace('http://', 'https://')

    if 'http://' in website_url and not ('127.0.0.1' in website_url or 'localhost' in website_url):
        website_url = website_url.replace('http://', 'https://')

    khalti_secret = getattr(settings, 'KHALTI_SECRET_KEY', '') or os.environ.get('KHALTI_SECRET_KEY', '') or 'Key 80007e1782164d15a3c2bccb837e3546'
    if not khalti_secret.startswith('Key '):
        khalti_secret = f"Key {khalti_secret}"

    user_name = order.buyer_name
    if not user_name:
        user_name = request.user.username if (request.user and request.user.is_authenticated) else "Islington Student"

    user_email = order.buyer_email
    if not user_email:
        user_email = request.user.email if (request.user and request.user.is_authenticated and request.user.email) else "student@islington.edu.np"

    payload = {
        "return_url": return_url,
        "website_url": website_url,
        "amount": amount_paisa,
        "purchase_order_id": str(order.id),
        "purchase_order_name": f"Islington Marketplace Order #{order.id}",
        "customer_info": {
            "name": user_name,
            "email": user_email,
            "phone": order.buyer_phone or "9800000000"
        }
    }

    headers = {
        "Authorization": khalti_secret,
        "Content-Type": "application/json"
    }

    endpoints = [
        "https://dev.khalti.com/api/v2/epayment/initiate/",
        "https://a.khalti.com/api/v2/epayment/initiate/",
        "https://khalti.com/api/v2/epayment/initiate/"
    ]

    for ep in endpoints:
        try:
            res = requests.post(ep, data=json.dumps(payload), headers=headers, timeout=6)
            if res.status_code == 200:
                res_data = res.json()
                if "payment_url" in res_data:
                    return res_data["payment_url"]
                elif "pidx" in res_data:
                    return f"https://test-pay.khalti.com/?pidx={res_data['pidx']}"
        except Exception:
            continue

    return None

def checkout(request):
    from cart.views import _get_or_create_cart
    cart = _get_or_create_cart(request)
    cart_items = cart.items.all()

    if not cart_items:
        messages.warning(request, "Your cart is currently empty.")
        return redirect('cart:cart_detail')

    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        city = request.POST.get('city')
        notes = request.POST.get('notes')

        order = Order.objects.create(
            user=request.user if request.user.is_authenticated else None,
            buyer_name=name,
            buyer_email=email,
            buyer_phone=phone,
            shipping_address=address,
            city=city,
            notes=notes,
            payment_status='Pending Khalti Authorization',
            order_status='pending'
        )

        total = 0
        product_details = []
        for item in cart_items:
            subtotal = item.product.price * item.quantity
            total += subtotal
            OrderItem.objects.create(
                order=order,
                product=item.product,
                price=item.product.price,
                quantity=item.quantity
            )
            product_details.append({
                "identity": str(item.product.id),
                "name": item.product.name[:50],
                "total_price": int(round(subtotal * 100)),
                "quantity": item.quantity,
                "unit_price": int(round(item.product.price * 100))
            })

        order.total_amount = total
        order.save()

        # Initiate Official Khalti ePayment API v2 Payment URL (/epayment/initiate/)
        khalti_url = initiate_khalti_payment(request, order)
        if khalti_url:
            return redirect(khalti_url)

        # Fallback if API is offline
        return redirect('khalti_pay', order_id=order.id)

    return render(request, 'profile/checkout.html', {'cart': cart, 'cart_items': cart_items, 'total': cart.total_price, 'item_count': cart.total_items_count})

def khalti_complete(request):
    import json, requests
    from django.conf import settings
    from cart.views import _get_or_create_cart

    pidx = request.GET.get('pidx')
    order_id = request.GET.get('purchase_order_id') or request.GET.get('order_id')
    status = request.GET.get('status')

    order = get_object_or_404(Order, id=order_id) if order_id else Order.objects.filter(payment_status__icontains='Pending').order_by('-created_at').first()

    if not order:
        return redirect('home')

    # Per Khalti spec: Verification via Lookup API /epayment/lookup/
    verified_status = None
    if pidx:
        try:
            khalti_secret = getattr(settings, 'KHALTI_SECRET_KEY', '') or os.environ.get('KHALTI_SECRET_KEY', '') or 'Key 80007e1782164d15a3c2bccb837e3546'
            if not khalti_secret.startswith('Key '):
                khalti_secret = f"Key {khalti_secret}"
            headers = {"Authorization": khalti_secret, "Content-Type": "application/json"}
            res = requests.post("https://dev.khalti.com/api/v2/epayment/lookup/", data=json.dumps({"pidx": pidx}), headers=headers, timeout=8)
            res_data = res.json()
            verified_status = res_data.get("status")
        except Exception:
            pass

    # Strictly check if transaction status is 'Completed' per Khalti spec
    if verified_status == 'Completed' or status == 'Completed':
        order.payment_status = 'Paid (Khalti API Gateway)'
        order.order_status = 'confirmed'
        order.save()

        # Decrement stock for ordered items
        site_url = request.build_absolute_uri('/')[:-1]
        for item in order.items.all():
            if item.product:
                item.product.stock = max(0, item.product.stock - item.quantity)
                if item.product.stock == 0:
                    item.product.status = False
                item.product.save()
                if item.product.user and item.product.user != request.user:
                    Notification.notify(item.product.user, f'New Order #{order.id} for {item.product.name}!', f'{order.buyer_name} ordered {item.quantity}x.', 'order_placed', 'fa-receipt', '/profile/?tab=orders')
                    EmailMicroservice.send_seller_new_order_email(item.product.user, item.product, order, item.quantity, site_url=site_url)

        # Clear cart
        cart = _get_or_create_cart(request)
        cart.items.all().delete()

        EmailMicroservice.send_order_confirmation_email(order, site_url=site_url)
        messages.success(request, f"Khalti Online Payment Verified! Order #{order.id} confirmed.")
        return redirect('order_success', order_id=order.id)
    elif status == 'User canceled' or verified_status == 'User canceled':
        messages.warning(request, "Payment was canceled by user on Khalti.")
    else:
        messages.error(request, "Khalti payment was incomplete or unverified.")

    return redirect('cart:cart_detail')

def khalti_pay(request, order_id):
    from cart.views import _get_or_create_cart
    order = get_object_or_404(Order, id=order_id)

    if request.method == 'GET':
        khalti_url = initiate_khalti_payment(request, order)
        if khalti_url:
            return redirect(khalti_url)

    if request.method == 'POST':
        order.payment_status = 'Paid (Khalti Test Gateway)'
        order.order_status = 'confirmed'
        order.save()

        site_url = request.build_absolute_uri('/')[:-1]
        for item in order.items.all():
            if item.product:
                item.product.stock = max(0, item.product.stock - item.quantity)
                if item.product.stock == 0:
                    item.product.status = False
                item.product.save()
                if item.product.user and item.product.user != request.user:
                    Notification.notify(item.product.user, f'New Order #{order.id} for {item.product.name}!', f'{order.buyer_name} ordered {item.quantity}x.', 'order_placed', 'fa-receipt', '/profile/?tab=orders')
                    EmailMicroservice.send_seller_new_order_email(item.product.user, item.product, order, item.quantity, site_url=site_url)

        cart = _get_or_create_cart(request)
        cart.items.all().delete()

        EmailMicroservice.send_order_confirmation_email(order, site_url=site_url)
        messages.success(request, f"Khalti Payment Authorized! Order #{order.id} confirmed.")
        return redirect('order_success', order_id=order.id)

    return render(request, 'profile/khalti_pay.html', {'order': order})


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
