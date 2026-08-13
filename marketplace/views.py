import json
from datetime import timedelta
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from products.models import Product, Category as ProductCategory, Order, OrderItem, Auction, Bid
from blog.models import Post
from sitesetting.models import Banner, Notification
from utils.email_microservice import EmailMicroservice

def home(request):
    p = Product.objects.select_related('category').filter(status=True, is_approved=True).order_by('-created_at')
    b = Post.objects.select_related('category').filter(status=True).order_by('-created_at')[:3]
    # Check and permanently close finished auctions
    for a in Auction.objects.filter(is_active=True, end_time__lte=timezone.now()):
        a.is_active = False
        a.save()
        if a.highest_bidder:
            # Transfer item to winning student
            a.product.stock = max(0, a.product.stock - 1)
            if a.product.stock == 0: a.product.status = False
            a.product.save()

            order = Order.objects.create(
                user=a.highest_bidder,
                buyer_name=a.highest_bidder.first_name or a.highest_bidder.username,
                buyer_phone='9800000000',
                buyer_email=a.highest_bidder.email,
                meetup_location='Block C Library Lobby',
                meetup_time='Afternoon (1:00 PM - 3:00 PM)',
                notes=f'Won 24h Auction for {a.title}',
                total_amount=a.current_bid,
                payment_method='auction_bid_won',
                payment_status='Pending (Collection Payment)',
                order_status='confirmed'
            )
            OrderItem.objects.create(order=order, product=a.product, product_name=a.product.name, price=a.current_bid, quantity=1)
            EmailMicroservice.send_auction_won_notification(a.highest_bidder, a.product.user, a)
            Notification.notify(a.highest_bidder, f"🎉 You Won Auction: {a.title}!", f"Winning bid: Rs. {a.current_bid:.2f}. See your order in dashboard.", 'auction_won', 'fa-trophy', '/profile/?tab=orders')
            if a.product.user:
                Notification.notify(a.product.user, f"Auction Closed for {a.title}!", f"Item won by {a.highest_bidder.username} at Rs. {a.current_bid:.2f}.", 'auction_ended', 'fa-check-circle', '/profile/?tab=orders')

    auctions = Auction.objects.filter(is_active=True, end_time__gt=timezone.now(), product__is_approved=True).select_related('product', 'product__category', 'highest_bidder', 'product__user').order_by('end_time')
    return render(request, 'home/home1.html', {
        'banners': Banner.objects.filter(is_active=True), 'products': p, 'featured_products': p[:8],
        'categories': ProductCategory.objects.all(), 'blogs': b, 'latest_blogs': b, 'auctions': auctions,
        'total_products': Product.objects.filter(is_approved=True).count(), 'total_categories': ProductCategory.objects.count(), 'total_blogs': Post.objects.count()
    })

def start_auction(request, product_id):
    if not request.user.is_authenticated:
        messages.error(request, "Please sign in to start an auction.")
        return redirect('student_login')
    p = get_object_or_404(Product, id=product_id)
    if p.user != request.user and not request.user.is_superuser:
        messages.error(request, "Permission denied.")
        return redirect('user_profile')

    start_price = float(request.POST.get('starting_bid') or p.price)
    auction, created = Auction.objects.get_or_create(
        product=p,
        defaults={
            'title': f'24h Auction: {p.name}',
            'starting_bid': start_price,
            'current_bid': start_price,
            'end_time': timezone.now() + timedelta(days=1),
            'is_active': True
        }
    )
    if not created:
        auction.starting_bid = start_price
        auction.current_bid = start_price
        auction.end_time = timezone.now() + timedelta(days=1)
        auction.highest_bidder = None
        auction.is_active = True
        auction.save()

    auction_url = request.build_absolute_uri('/#liveBiddingSection')
    EmailMicroservice.send_new_auction_broadcast(auction, auction_url)
    Notification.notify_all(f'🔥 24h Live Auction: {p.name}', f'{request.user.first_name or request.user.username} started an auction starting at Rs. {start_price:.2f}!', 'auction_start', 'fa-gavel', '/#liveBiddingSection', exclude_user=request.user)
    messages.success(request, f"24-Hour Live Auction started for {p.name}! Notification sent to students.")
    return redirect('home')

def accept_auction_bid(request, auction_id):
    if not request.user.is_authenticated:
        messages.error(request, "Please sign in.")
        return redirect('student_login')
    auction = get_object_or_404(Auction, id=auction_id, is_active=True)
    if auction.product.user != request.user and not request.user.is_superuser:
        messages.error(request, "Only the publisher can accept the bid.")
        return redirect('home')

    if not auction.highest_bidder:
        messages.error(request, "No bids have been placed yet to accept.")
        return redirect('home')

    # Permanently close auction and decrement stock
    auction.is_active = False
    auction.save()

    auction.product.stock = max(0, auction.product.stock - 1)
    if auction.product.stock == 0: auction.product.status = False
    auction.product.save()

    winner = auction.highest_bidder
    order = Order.objects.create(
        user=winner,
        buyer_name=winner.first_name or winner.username,
        buyer_phone='9800000000',
        buyer_email=winner.email,
        meetup_location='Block C Library Lobby',
        meetup_time='Afternoon (1:00 PM - 3:00 PM)',
        notes=f'Accepted Early by Seller for {auction.title}',
        total_amount=auction.current_bid,
        payment_method='auction_bid_won',
        payment_status='Pending (Collection Payment)',
        order_status='confirmed'
    )
    OrderItem.objects.create(order=order, product=auction.product, product_name=auction.product.name, price=auction.current_bid, quantity=1)

    EmailMicroservice.send_auction_won_notification(winner, request.user, auction)
    Notification.notify(winner, f"🎉 Seller Accepted Your Bid for {auction.title}!", f"Winning price: Rs. {auction.current_bid:.2f}. See details in My Orders.", 'auction_won', 'fa-trophy', '/profile/?tab=orders')
    Notification.notify(request.user, f"Auction Closed for {auction.title}", f"Accepted winning bid of Rs. {auction.current_bid:.2f} from {winner.username}.", 'auction_ended', 'fa-check-circle', '/profile/?tab=orders')

    messages.success(request, f"Success! You accepted the highest bid of Rs. {auction.current_bid:.2f} from {winner.username}. Auction closed permanently!")
    return redirect('home')

def place_bid(request, auction_id):
    if not request.user.is_authenticated:
        messages.error(request, "Please sign in to place a bid on student auctions.")
        return redirect('student_login')
    auction = get_object_or_404(Auction, id=auction_id, is_active=True)
    if auction.product.user == request.user:
        messages.error(request, "You cannot bid on your own listing.")
        return redirect('home')

    if request.method == 'POST':
        try: bid_amount = float(request.POST.get('bid_amount', 0))
        except (ValueError, TypeError):
            messages.error(request, "Invalid bid amount.")
            return redirect('home')
        if bid_amount <= auction.current_bid:
            messages.error(request, f"Your bid must be higher than current bid of Rs. {auction.current_bid:.2f}")
            return redirect('home')

        old_bidder = auction.highest_bidder
        Bid.objects.create(auction=auction, user=request.user, amount=bid_amount)
        auction.current_bid = bid_amount
        auction.highest_bidder = request.user
        auction.save()

        # Resend Email Notification to Outbid Student
        if old_bidder and old_bidder != request.user:
            auction_url = request.build_absolute_uri('/#liveBiddingSection')
            EmailMicroservice.send_outbid_notification(old_bidder, auction, bid_amount, auction_url)
            Notification.notify(old_bidder, f"Outbid on {auction.product.name}!", f"New highest bid: Rs. {bid_amount:.2f}.", 'auction_outbid', 'fa-arrow-up', '/#liveBiddingSection')

        if auction.product.user and auction.product.user != request.user:
            Notification.notify(auction.product.user, f"New Bid Rs. {bid_amount:.2f} on {auction.product.name}!", f"{request.user.first_name or request.user.username} placed a new highest bid.", 'auction_bid', 'fa-gavel', f'/products/{auction.product.id}/')

        messages.success(request, f"Success! Your bid of Rs. {bid_amount:.2f} is currently the highest bid.")
    return redirect('home')

def user_profile(request):
    u = request.user
    if request.method == 'POST' and u.is_authenticated:
        act, post = request.POST.get('action'), request.POST
        if act == 'update_profile':
            u.first_name, u.last_name, u.email = post.get('first_name', u.first_name), post.get('last_name', u.last_name), post.get('email', u.email)
            u.save(); messages.success(request, "Profile updated!")
        elif act == 'add_product' and post.get('name') and post.get('category') and post.get('price'):
            is_staff_user = u.is_superuser or u.is_staff
            p = Product.objects.create(
                user=u,
                name=post['name'].strip(),
                category_id=post['category'],
                price=float(post['price']),
                stock=int(post.get('stock') or 1),
                description=post.get('description', '').strip(),
                product_image=request.FILES.get('product_image'),
                status=True if is_staff_user else False,
                is_approved=True if is_staff_user else False
            )
            if is_staff_user:
                if post.get('start_as_auction') == '1':
                    a = Auction.objects.create(
                        product=p,
                        title=f'24h Auction: {p.name}',
                        starting_bid=float(post.get('starting_bid') or p.price),
                        current_bid=float(post.get('starting_bid') or p.price),
                        end_time=timezone.now() + timedelta(days=1),
                        is_active=True
                    )
                    auction_url = request.build_absolute_uri('/#liveBiddingSection')
                    EmailMicroservice.send_new_auction_broadcast(a, auction_url)
                    Notification.notify_all(f'🔥 24h Live Auction: {p.name}', f'{u.first_name or u.username} started an auction for "{p.name}"!', 'auction_start', 'fa-gavel', '/#liveBiddingSection', exclude_user=u)
                Notification.notify(u, f'Listing "{p.name}" is live!', f'Rs. {p.price}', 'product_listed', 'fa-check-circle', f'/products/{p.id}/')
                Notification.notify_all(f'New: {p.name}', f'{u.first_name or u.username} listed "{p.name}" for Rs. {p.price}.', 'product_listed', 'fa-box-open', f'/products/{p.id}/', exclude_user=u)
                EmailMicroservice.send_product_listed_email(u, p)
                messages.success(request, f'"{p.name}" published successfully and is now live on the store!')
            else:
                Notification.notify(u, f'Listing Submitted for Review: {p.name}', f'Your listing "{p.name}" is under review by college admin and will appear on the store once approved.', 'product_pending', 'fa-clock', '/profile/?tab=products')
                messages.success(request, f'Listing "{p.name}" submitted! It is currently under review by admin and will appear publicly once approved.')
        elif act == 'edit_product':
            p = get_object_or_404(Product, id=post.get('product_id'))
            if p.user == u or u.is_superuser:
                p.name, p.price, p.stock, p.description = post.get('name', p.name), float(post.get('price', p.price)), int(post.get('stock', p.stock)), post.get('description', p.description)
                if post.get('category'): p.category_id = post['category']
                if request.FILES.get('product_image'): p.product_image = request.FILES['product_image']
                p.save(); messages.success(request, f'"{p.name}" updated!')
        elif act == 'delete_product':
            p = get_object_or_404(Product, id=post.get('product_id'))
            if p.user == u or u.is_superuser: p.delete(); messages.success(request, "Listing removed.")
        return redirect('user_profile')

    user_prods = Product.objects.filter(user=u).select_related('category').order_by('-created_at') if u.is_authenticated else Product.objects.select_related('category').all()[:6]
    user_orders = Order.objects.filter(user=u).prefetch_related('items').order_by('-created_at') if u.is_authenticated else []
    user_sales = OrderItem.objects.filter(product__user=u).select_related('order', 'product').order_by('-order__created_at') if u.is_authenticated else []
    return render(request, 'profile/profile.html', {
        'profile_user': u, 'user_products': user_prods, 'user_orders': user_orders, 'user_sales': user_sales, 'categories': ProductCategory.objects.all()
    })

def checkout(request):
    if request.method == 'POST':
        post = request.POST
        try: cart = json.loads(post.get('cart_json', '[]'))
        except Exception: cart = []
        if not cart: messages.error(request, "Your shopping bag is empty."); return redirect('products')

        order = Order.objects.create(
            user=request.user if request.user.is_authenticated else None,
            buyer_name=post.get('buyer_name', '').strip(), buyer_phone=post.get('buyer_phone', '').strip(),
            buyer_email=post.get('buyer_email', '').strip(), meetup_location=post.get('meetup_location', 'Block C Library Lobby'),
            meetup_time=post.get('meetup_time', 'Morning (10:00 AM - 12:00 PM)'), notes=post.get('notes', '').strip(),
            payment_method=post.get('payment_method', 'esewa_sandbox'), payment_status='Paid (Online Sandbox)', order_status='confirmed'
        )
        total = 0.0
        for item in cart:
            pid, qty, pr = item.get('id'), int(item.get('quantity') or 1), float(item.get('price') or 0.0)
            prod = Product.objects.filter(id=pid).first() if pid else None
            OrderItem.objects.create(order=order, product=prod, product_name=item.get('name', 'Product'), price=pr, quantity=qty)
            total += pr * qty
            if prod and prod.user:
                Notification.notify(prod.user, f'New Order #{order.id} for {prod.name}!', f'{order.buyer_name} ordered {qty}x {prod.name}. Pickup: {order.meetup_location}', 'order_placed', 'fa-receipt', f'/profile/?tab=orders')

        order.total_amount = total; order.save()
        site_url = request.build_absolute_uri('/')[:-1]
        EmailMicroservice.send_order_confirmation_email(order, site_url=site_url)
        if request.user.is_authenticated:
            Notification.notify(request.user, f'Order #{order.id} Confirmed!', f'Total Rs. {total:.2f}. Pickup: {order.meetup_location}', 'order_placed', 'fa-check-circle', f'/profile/?tab=orders')

        return redirect('order_success', order_id=order.id)
    return render(request, 'profile/checkout.html')

def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'profile/order_success.html', {'order': order})

def student_login(request):
    if request.user.is_authenticated: return redirect('user_profile')
    if request.method == 'POST':
        u = authenticate(request, username=request.POST.get('username', '').strip(), password=request.POST.get('password', ''))
        if u: login(request, u); messages.success(request, f"Welcome back, {u.first_name or u.username}!"); return redirect('user_profile')
        messages.error(request, "Invalid student credentials or unverified account.")
    return render(request, 'profile/login.html')

def student_register(request):
    if request.user.is_authenticated: return redirect('user_profile')
    if request.method == 'POST':
        u, em, pw, cpw = request.POST.get('username', '').strip(), request.POST.get('email', '').strip(), request.POST.get('password', ''), request.POST.get('confirm_password', '')
        if not u or not em or not pw: messages.error(request, "All fields required.")
        elif pw != cpw: messages.error(request, "Passwords do not match.")
        elif User.objects.filter(username=u).exists(): messages.error(request, "Username taken.")
        elif User.objects.filter(email=em).exists(): messages.error(request, "Email already in use.")
        else:
            usr = User.objects.create_user(username=u, email=em, password=pw, first_name=request.POST.get('first_name', '').strip(), last_name=request.POST.get('last_name', '').strip(), is_active=False)
            token = TimestampSigner().sign(usr.username)
            verify_url = request.build_absolute_uri(f'/verify-email/{token}/')
            EmailMicroservice.send_verification_email(usr, verify_url)
            messages.success(request, "Registration successful! Please check your email to verify your account.")
            return redirect('student_login')
    return render(request, 'profile/register.html')

def verify_email(request, token):
    try:
        username = TimestampSigner().unsign(token, max_age=86400)
        user = User.objects.get(username=username)
        user.is_active = True; user.save(); login(request, user)
        Notification.notify(user, f'Welcome, {user.first_name or user.username}!', 'Account verified! Explore listings or start selling.', 'welcome', 'fa-check-circle', '/profile/')
        messages.success(request, "Email verified successfully! Your account is now active.")
        return redirect('user_profile')
    except (BadSignature, SignatureExpired, User.DoesNotExist):
        messages.error(request, "Invalid or expired verification link.")
        return redirect('student_login')

def student_logout(request):
    logout(request); messages.success(request, "Logged out."); return redirect('home')

def custom_404(request, exception=None): return render(request, '404.html', status=404)
