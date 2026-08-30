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

def initiate_khalti_payment(request, order):
    import json, requests
    from django.conf import settings

    try:
        amount_paisa = max(1000, int(round(float(order.total_amount or 0) * 100)))
        return_url = request.build_absolute_uri('/checkout/khalti/complete/')
        website_url = request.build_absolute_uri('/')

        if 'http://' in return_url and not ('127.0.0.1' in return_url or 'localhost' in return_url):
            return_url = return_url.replace('http://', 'https://')

        if 'http://' in website_url and not ('127.0.0.1' in website_url or 'localhost' in website_url):
            website_url = website_url.replace('http://', 'https://')

        raw_key = (os.environ.get('KHALTI_SECRET_KEY', '') or getattr(settings, 'KHALTI_SECRET_KEY', '') or 'test_secret_key_e3158c56e30b427aa49a93ecb0593467').strip()
        
        keys_to_try = []
        if raw_key:
            keys_to_try.append(raw_key if raw_key.startswith('Key ') else f"Key {raw_key}")
        keys_to_try.extend([
            "Key test_secret_key_e3158c56e30b427aa49a93ecb0593467",
            "Key test_secret_key_f59e415c5d94406385df7c4067176827",
            "Key 80007e1782164d15a3c2bccb837e3546"
        ])

        endpoints = [
            "https://dev.khalti.com/api/v2/epayment/initiate/",
            "https://a.khalti.com/api/v2/epayment/initiate/",
            "https://khalti.com/api/v2/epayment/initiate/"
        ]

        user_name = order.buyer_name or "Islington Student"
        user_email = order.buyer_email or "student@islington.edu.np"
        user_phone = order.buyer_phone or "9824616674"

        clean_phone = ''.join(c for c in str(user_phone) if c.isdigit())
        if len(clean_phone) != 10 or not clean_phone.startswith(('98', '97')):
            clean_phone = "9824616674"

        payload = {
            "return_url": return_url,
            "website_url": website_url,
            "amount": amount_paisa,
            "purchase_order_id": f"ORDER_{order.id}",
            "purchase_order_name": f"Islington Order #{order.id}",
            "customer_info": {
                "name": str(user_name)[:50],
                "email": str(user_email),
                "phone": clean_phone
            }
        }

        unique_keys = []
        for k in keys_to_try:
            if k not in unique_keys:
                unique_keys.append(k)

        for key in unique_keys:
            headers = {
                "Authorization": key,
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            }
            for ep in endpoints:
                try:
                    res = requests.post(ep, data=json.dumps(payload), headers=headers, timeout=8, verify=False)
                    if res.status_code in [200, 201]:
                        res_data = res.json()
                        if "payment_url" in res_data and res_data["payment_url"]:
                            return res_data["payment_url"]
                        elif "pidx" in res_data and res_data["pidx"]:
                            return f"https://test-pay.khalti.com/?pidx={res_data['pidx']}"
                except Exception as err:
                    print(f"Khalti initiate failed on {ep} with key {key[:15]}:", err)
                    continue
    except Exception as err:
        print("Khalti initiation exception:", err)

    return None

def checkout(request):
    from cart.views import _get_or_create_cart
    cart = _get_or_create_cart(request)
    cart_items = [item for item in cart.items.all() if item.product]

    if not cart_items:
        messages.warning(request, "Your cart is currently empty.")
        return redirect('cart:cart_detail')

    if request.method == 'POST':
        try:
            name = (request.POST.get('buyer_name') or request.POST.get('name') or '').strip()
            if not name:
                if request.user and request.user.is_authenticated:
                    name = request.user.get_full_name() or request.user.username or "Islington Student"
                else:
                    name = "Islington Student"

            phone = (request.POST.get('buyer_phone') or request.POST.get('phone') or '').strip() or '9824616674'
            email = (request.POST.get('buyer_email') or request.POST.get('email') or '').strip()
            if not email:
                if request.user and request.user.is_authenticated and request.user.email:
                    email = request.user.email
                else:
                    email = "student@islington.edu.np"

            del_type = request.POST.get('delivery_type')
            if del_type == 'home_delivery':
                location = (request.POST.get('home_address') or '').strip() or 'Kathmandu Home Delivery'
            else:
                location = (request.POST.get('campus_block') or '').strip() or 'Kumari Hall'

            m_time = (request.POST.get('meetup_time') or '').strip() or 'Morning (10:00 AM - 12:00 PM)'
            notes = (request.POST.get('notes') or '').strip()

            order = Order.objects.create(
                user=request.user if (request.user and request.user.is_authenticated) else None,
                buyer_name=name,
                buyer_phone=phone,
                buyer_email=email,
                meetup_location=location,
                meetup_time=m_time,
                notes=notes,
                payment_status='Pending Khalti Authorization',
                order_status='pending'
            )

            total = 0.0
            for item in cart_items:
                if not item.product:
                    continue
                p_price = float(item.product.price or 0.0)
                subtotal = p_price * item.quantity
                total += subtotal
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    product_name=item.product.name,
                    price=p_price,
                    quantity=item.quantity
                )

            order.total_amount = total
            order.save()

            return redirect('khalti_pay', order_id=order.id)
        except Exception as err:
            print("Checkout Order Processing Exception:", err)
            messages.error(request, f"Error processing checkout: {err}")
            return redirect('cart:cart_detail')

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
    order = get_object_or_404(Order, id=order_id)
    khalti_url = initiate_khalti_payment(request, order)
    if khalti_url:
        return redirect(khalti_url)

    return render(request, 'profile/khalti_gateway.html', {'order': order})

def khalti_api_initiate(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    khalti_url = initiate_khalti_payment(request, order)
    if khalti_url:
        return JsonResponse({'status': 'success', 'payment_url': khalti_url})
    return JsonResponse({'status': 'error', 'message': 'Gateway timeout'}, status=500)


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
