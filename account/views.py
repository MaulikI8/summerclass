import random
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse

from products.models import Product, Category, Order, OrderItem, TradeOffer, Wishlist
from blog.models import Post as BlogPost
from sitesetting.models import Notification, EmailOTP
from utils.email_microservice import EmailMicroservice

def student_login(request):
    if request.user.is_authenticated: return redirect('user_profile')
    username = ''
    if request.method == 'POST':
        username, pwd = request.POST.get('username', '').strip(), request.POST.get('password', '')
        user = authenticate(request, username=username, password=pwd)
        if user:
            old_session_key = request.session.session_key
            login(request, user)
            try:
                from products.models import SearchHistory, ProductView
                if old_session_key:
                    SearchHistory.objects.filter(session_key=old_session_key, user__isnull=True).update(user=user)
                    ProductView.objects.filter(session_key=old_session_key, user__isnull=True).update(user=user)
            except Exception:
                pass
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            return redirect('user_profile')
        
        inactive = User.objects.filter(username=username).first()
        if inactive and inactive.check_password(pwd):
            uid = urlsafe_base64_encode(force_bytes(inactive.pk))
            token = default_token_generator.make_token(inactive)
            activation_url = request.build_absolute_uri(reverse('activate_account', kwargs={'uidb64': uid, 'token': token}))
            EmailMicroservice.send_activation_email(inactive, activation_url)
            messages.info(request, f"Your account is not activated yet. A new activation link has been sent to {inactive.email}.")
            return redirect('student_login')

        messages.error(request, "Invalid credentials.")
    return render(request, 'profile/login.html', {'saved_username': username})

def student_register(request):
    if request.user.is_authenticated: return redirect('user_profile')
    if request.method == 'POST':
        p = request.POST
        u, em, pw, cpw = p.get('username', '').strip(), p.get('email', '').strip(), p.get('password', ''), p.get('confirm_password', '')
        if not (u and em and pw) or pw != cpw:
            messages.error(request, "Passwords do not match or fields missing.")
        elif User.objects.filter(username=u).exists() or User.objects.filter(email=em).exists():
            messages.error(request, "Username or email already in use.")
        else:
            usr = User.objects.create_user(username=u, email=em, password=pw, first_name=p.get('first_name', ''), last_name=p.get('last_name', ''), is_active=False)
            uid = urlsafe_base64_encode(force_bytes(usr.pk))
            token = default_token_generator.make_token(usr)
            activation_url = request.build_absolute_uri(reverse('activate_account', kwargs={'uidb64': uid, 'token': token}))
            EmailMicroservice.send_activation_email(usr, activation_url)
            messages.success(request, f"Registration successful! We sent an activation link to {usr.email}. Please check your inbox to activate your account.")
            return redirect('student_login')
    return render(request, 'profile/register.html')

def activate_account(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        usr = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        usr = None

    if usr is not None and default_token_generator.check_token(usr, token):
        usr.is_active = True
        usr.save()
        login(request, usr)
        Notification.notify(usr, f'Welcome {usr.username}!', 'Account activated via email link! Start exploring marketplace.', 'welcome', 'fa-check-circle', '/profile/')
        messages.success(request, f"Account activated successfully! Welcome to Islington Marketplace, {usr.first_name or usr.username}.")
        return redirect('user_profile')
    else:
        messages.error(request, "Activation link is invalid or has expired.")
        return redirect('student_login')

def verify_otp(request):
    return redirect('student_login')

def resend_otp(request):
    return redirect('student_login')

def verify_email(request, token):
    return redirect('student_login')

def student_logout(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect('home')

def user_profile(request):
    u = request.user
    if request.method == 'POST' and u.is_authenticated:
        act, post = request.POST.get('action'), request.POST
        if act == 'update_profile':
            u.first_name, u.last_name, u.email = post.get('first_name', u.first_name), post.get('last_name', u.last_name), post.get('email', u.email)
            u.save()
            messages.success(request, "Profile updated!")
        elif act == 'add_product' and post.get('name') and post.get('price'):
            p = Product.objects.create(
                user=u, name=post['name'].strip(), category_id=post.get('category') or 1,
                price=float(post['price']), stock=int(post.get('stock') or 1),
                description=post.get('description', '').strip(),
                product_image=request.FILES.get('product_image'), status=False, is_approved=False
            )
            EmailMicroservice.send_admin_new_pending_review_email(p, u, request.build_absolute_uri('/admin/products/pendingproductreview/'))
            Notification.notify(u, f'Listing Submitted: {p.name}', 'Under admin review.', 'product_pending', 'fa-clock', '/profile/?tab=products')
            messages.success(request, f'Listing "{p.name}" submitted for approval.')
        elif act in ('edit_product', 'delete_product'):
            p = get_object_or_404(Product, id=post.get('product_id'))
            if p.user == u or u.is_superuser:
                if act == 'delete_product': p.delete()
                else:
                    p.name, p.price, p.stock, p.description = post.get('name', p.name), float(post.get('price', p.price)), int(post.get('stock', p.stock)), post.get('description', p.description)
                    if post.get('category'): p.category_id = post['category']
                    if request.FILES.get('product_image'): p.product_image = request.FILES['product_image']
                    p.save()
                messages.success(request, "Listing updated.")
        return redirect('user_profile')

    return render(request, 'profile/profile.html', {
        'profile_user': u,
        'user_products': Product.objects.filter(user=u).select_related('category').order_by('-created_at') if u.is_authenticated else [],
        'user_orders': Order.objects.filter(user=u).prefetch_related('items').order_by('-created_at') if u.is_authenticated else [],
        'user_sales': OrderItem.objects.filter(product__user=u).select_related('order', 'product').order_by('-order__created_at') if u.is_authenticated else [],
        'user_blogs': BlogPost.objects.filter(author=u).select_related('category').order_by('-created_at') if u.is_authenticated else [],
        'user_recv_offers': TradeOffer.objects.filter(receiver=u).select_related('product', 'sender').order_by('-created_at') if u.is_authenticated else [],
        'user_sent_offers': TradeOffer.objects.filter(sender=u).select_related('product', 'receiver').order_by('-created_at') if u.is_authenticated else [],
        'user_wishlist': Wishlist.objects.filter(user=u).select_related('product', 'product__category').order_by('-created_at') if u.is_authenticated else [],
        'categories': Category.objects.all()
    })
