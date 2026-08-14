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
    try:
        p = list(Product.objects.select_related('category').filter(status=True, is_approved=True).order_by('-created_at'))
    except Exception:
        p = []
    try:
        b = list(Post.objects.select_related('category').filter(status=True).order_by('-created_at')[:3])
    except Exception:
        b = []
    try:
        # Check and permanently close finished auctions
        for a in Auction.objects.filter(is_active=True, end_time__lte=timezone.now()):
            a.is_active = False
            a.save()
            if a.highest_bidder:
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

        auctions = list(Auction.objects.filter(is_active=True, end_time__gt=timezone.now(), product__is_approved=True).select_related('product', 'product__category', 'highest_bidder', 'product__user').order_by('end_time'))
    except Exception:
        auctions = []

    try: banners = list(Banner.objects.filter(is_active=True))
    except Exception: banners = []

    try: categories = list(ProductCategory.objects.all())
    except Exception: categories = []

    return render(request, 'home/home1.html', {
        'banners': banners, 'products': p, 'featured_products': p[:8],
        'categories': categories, 'blogs': b, 'latest_blogs': b, 'auctions': auctions,
        'total_products': len(p), 'total_categories': len(categories), 'total_blogs': len(b)
    })

def start_auction(request, product_id):
    if not request.user.is_authenticated:
        messages.error(request, "Please sign in to start an auction.")
        return redirect('student_login')
    p = get_object_or_404(Product, id=product_id)
    if p.user != request.user and not request.user.is_superuser:
        messages.error(request, "Permission denied.")
        return redirect('user_profile')
    if not p.is_approved:
        messages.error(request, f'Listing "{p.name}" is pending admin review. It can only be put on auction once approved by admin.')
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
        messages.error(request, "Only the seller can accept the highest bid.")
        return redirect('home')

    if not auction.highest_bidder:
        messages.error(request, "No bids have been placed yet.")
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
        notes=f'Publisher accepted early winning bid of Rs. {auction.current_bid:.2f}',
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

def checkout(request):
    from cart.views import _get_or_create_cart
    cart = _get_or_create_cart(request)
    cart_items = cart.items.filter(is_active=True).select_related('product', 'product__user')

    if not cart_items.exists():
        messages.warning(request, "Your shopping bag is empty. Please add items to checkout.")
        return redirect('products')

    # Prevent sellers from buying their own products
    if request.user.is_authenticated:
        for item in cart_items:
            if item.product and item.product.user == request.user:
                messages.error(request, f"You cannot purchase your own item: '{item.product.name}'. Please remove it from your bag to proceed.")
                return redirect('cart:cart_detail')

    if request.method == 'POST':
        post = request.POST
        delivery_type = post.get('delivery_type', 'campus_pickup')
        if delivery_type == 'home_delivery':
            home_addr = post.get('home_address', '').strip()
            city = post.get('delivery_city', 'Kathmandu').strip()
            meetup_loc = f"Home Delivery: {home_addr}, {city}" if home_addr else "Home Delivery (Kathmandu)"
            meetup_tm = post.get('home_delivery_time', 'Anytime (9:00 AM - 6:00 PM)')
        else:
            block = post.get('campus_block', 'Kumari Hall').strip()
            meetup_loc = f"Campus Block: {block}"
            meetup_tm = post.get('meetup_time', 'Morning (10:00 AM - 12:00 PM)')

        order = Order.objects.create(
            user=request.user if request.user.is_authenticated else None,
            buyer_name=post.get('buyer_name', '').strip(),
            buyer_phone=post.get('buyer_phone', '').strip(),
            buyer_email=post.get('buyer_email', '').strip(),
            meetup_location=meetup_loc,
            meetup_time=meetup_tm,
            notes=post.get('notes', '').strip(),
            payment_method=post.get('payment_method', 'esewa_sandbox'),
            payment_status='Paid (Online Sandbox)',
            order_status='confirmed'
        )
        total = 0.0
        site_url = request.build_absolute_uri('/')[:-1]
        for item in cart_items:
            prod = item.product
            pr = float(prod.price) if prod else 0.0
            qty = item.quantity
            OrderItem.objects.create(order=order, product=prod, product_name=prod.name if prod else 'Product', price=pr, quantity=qty)
            total += pr * qty
            if prod and prod.user and prod.user != request.user:
                Notification.notify(prod.user, f'New Order #{order.id} for {prod.name}!', f'{order.buyer_name} ordered {qty}x {prod.name}. Pickup/Delivery: {order.meetup_location}', 'order_placed', 'fa-receipt', f'/profile/?tab=orders')
                EmailMicroservice.send_seller_new_order_email(prod.user, prod, order, qty, site_url=site_url)

        order.total_amount = total
        order.save()

        # Clear cart upon successful order
        cart_items.delete()

        EmailMicroservice.send_order_confirmation_email(order, site_url=site_url)
        if request.user.is_authenticated:
            Notification.notify(request.user, f'Order #{order.id} Confirmed!', f'Total Rs. {total:.2f}. Pickup/Delivery: {order.meetup_location}', 'order_placed', 'fa-check-circle', f'/profile/?tab=orders')

        return redirect('order_success', order_id=order.id)

    return render(request, 'profile/checkout.html', {
        'cart': cart,
        'cart_items': cart_items,
        'total': cart.total_price,
        'item_count': cart.total_items_count,
    })

def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'profile/order_success.html', {'order': order})

def custom_404(request, exception=None): return render(request, '404.html', status=404)
