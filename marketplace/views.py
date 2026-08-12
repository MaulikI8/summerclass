import json
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
    p = Product.objects.select_related('category').filter(status=True).order_by('-created_at') or Product.objects.select_related('category').all().order_by('-created_at')
    b = Post.objects.select_related('category').filter(status=True).order_by('-created_at')[:3]
    auctions = Auction.objects.filter(is_active=True).select_related('product', 'product__category', 'highest_bidder', 'product__user').order_by('end_time')
    return render(request, 'home/home1.html', {
        'banners': Banner.objects.filter(is_active=True), 'products': p, 'featured_products': p[:8],
        'categories': ProductCategory.objects.all(), 'blogs': b, 'latest_blogs': b, 'auctions': auctions,
        'total_products': Product.objects.count(), 'total_categories': ProductCategory.objects.count(), 'total_blogs': Post.objects.count()
    })

def place_bid(request, auction_id):
    if not request.user.is_authenticated:
        messages.error(request, "Please sign in to place a bid on student auctions.")
        return redirect('student_login')
    auction = get_object_or_404(Auction, id=auction_id, is_active=True)
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

        if auction.product.user and auction.product.user != request.user:
            Notification.notify(auction.product.user, f"New Bid Rs. {bid_amount:.2f} on {auction.product.name}!", f"{request.user.first_name or request.user.username} placed a new highest bid.", 'auction_bid', 'fa-gavel', f'/products/{auction.product.id}/')
        if old_bidder and old_bidder != request.user:
            Notification.notify(old_bidder, f"Outbid on {auction.product.name}!", f"New highest bid: Rs. {bid_amount:.2f}.", 'auction_outbid', 'fa-arrow-up', '/#liveBiddingSection')

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
            p = Product.objects.create(user=u, name=post['name'].strip(), category_id=post['category'], price=float(post['price']), stock=int(post.get('stock') or 1), description=post.get('description', '').strip(), product_image=request.FILES.get('product_image'), status=True)
            Notification.notify(u, f'Listing "{p.name}" is live!', f'Rs. {p.price}', 'product_listed', 'fa-check-circle', f'/products/{p.id}/')
            Notification.notify_all(f'New: {p.name}', f'{u.first_name or u.username} listed "{p.name}" for Rs. {p.price}.', 'product_listed', 'fa-box-open', f'/products/{p.id}/', exclude_user=u)
            EmailMicroservice.send_product_listed_email(u, p)
            messages.success(request, f'"{p.name}" published!')
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
