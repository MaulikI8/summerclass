import random
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.contrib.auth.decorators import login_required
from products.models import Product, Category, Order, OrderItem
from blog.models import Post as BlogPost
from sitesetting.models import Notification, EmailOTP
from utils.email_microservice import EmailMicroservice

def student_login(request):
    """
    Handles student login with session preservation and inactive account verification check.
    """
    if request.user.is_authenticated:
        return redirect('user_profile')

    entered_username = ''
    if request.method == 'POST':
        entered_username = request.POST.get('username', '').strip()
        pwd = request.POST.get('password', '')
        u = authenticate(request, username=entered_username, password=pwd)
        if u:
            login(request, u)
            messages.success(request, f"Welcome back, {u.first_name or u.username}!")
            return redirect('user_profile')
        else:
            # Check if user exists but has unverified inactive account
            inactive_user = User.objects.filter(username=entered_username).first()
            if inactive_user and inactive_user.check_password(pwd):
                # Send a new OTP and redirect to verification
                otp_code = f"{random.randint(100000, 999999):06d}"
                EmailOTP.objects.filter(user=inactive_user, is_used=False).update(is_used=True)
                EmailOTP.objects.create(user=inactive_user, otp_code=otp_code, purpose='login_activation')
                EmailMicroservice.send_otp_email(inactive_user, otp_code)
                request.session['pending_otp_user_id'] = inactive_user.id
                messages.info(request, f"Please enter the 6-digit verification code sent to {inactive_user.email} to activate your account.")
                return redirect('verify_otp')
            messages.error(request, "Invalid student credentials or wrong password.")
    return render(request, 'profile/login.html', {'saved_username': entered_username})

def student_register(request):
    """
    Registers a new student account, sends 6-digit Email OTP via Google SMTP,
    and forwards to OTP verification screen.
    """
    if request.user.is_authenticated:
        return redirect('user_profile')

    form_data = {}
    if request.method == 'POST':
        form_data = request.POST
        u = request.POST.get('username', '').strip()
        em = request.POST.get('email', '').strip()
        pw = request.POST.get('password', '')
        cpw = request.POST.get('confirm_password', '')

        if not u or not em or not pw:
            messages.error(request, "All fields are required.")
        elif pw != cpw:
            messages.error(request, "Passwords do not match.")
        elif User.objects.filter(username=u).exists():
            messages.error(request, "Username is already taken. Please choose another.")
        elif User.objects.filter(email=em).exists():
            messages.error(request, "Email is already registered. Please sign in instead.")
        else:
            usr = User.objects.create_user(
                username=u,
                email=em,
                password=pw,
                first_name=request.POST.get('first_name', '').strip(),
                last_name=request.POST.get('last_name', '').strip(),
                is_active=False
            )
            # Generate 6-Digit Email OTP
            otp_code = f"{random.randint(100000, 999999):06d}"
            EmailOTP.objects.create(user=usr, otp_code=otp_code, purpose='registration')
            EmailMicroservice.send_otp_email(usr, otp_code)

            request.session['pending_otp_user_id'] = usr.id
            messages.success(request, f"Verification code sent to {usr.email}. Please enter the 6-digit OTP to activate your account.")
            return redirect('verify_otp')
    return render(request, 'profile/register.html', {'form_data': form_data})

def verify_otp(request):
    """
    Verifies 6-digit numeric OTP code, activates user account, and logs the student in.
    """
    if request.user.is_authenticated:
        return redirect('user_profile')
    
    user_id = request.session.get('pending_otp_user_id')
    if not user_id:
        messages.info(request, "Please register or sign in to verify your account.")
        return redirect('student_login')

    try:
        pending_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, "User session expired. Please register again.")
        return redirect('student_register')

    if request.method == 'POST':
        entered_otp = request.POST.get('otp_code', '').strip().replace(' ', '')
        
        active_otps = EmailOTP.objects.filter(user=pending_user, is_used=False).order_by('-created_at')
        valid_otp = None
        for otp_obj in active_otps:
            if otp_obj.is_valid() and otp_obj.otp_code == entered_otp:
                valid_otp = otp_obj
                break

        if valid_otp:
            valid_otp.is_used = True
            valid_otp.save()

            pending_user.is_active = True
            pending_user.save()

            login(request, pending_user)
            if 'pending_otp_user_id' in request.session:
                del request.session['pending_otp_user_id']

            Notification.notify(
                pending_user,
                f'Welcome to Islington Marketplace, {pending_user.first_name or pending_user.username}!',
                'Email verified successfully! You can now list items and trade with peers.',
                'welcome',
                'fa-check-circle',
                '/profile/'
            )
            messages.success(request, f"Welcome {pending_user.first_name or pending_user.username}! Your account has been verified successfully.")
            return redirect('user_profile')
        else:
            messages.error(request, "Invalid or expired 6-digit code. Please check your inbox or click 'Resend Code'.")

    return render(request, 'profile/verify_otp.html', {'pending_user': pending_user})

def resend_otp(request):
    """
    Regenerates a fresh 6-digit OTP and dispatches it via Google SMTP.
    """
    user_id = request.session.get('pending_otp_user_id')
    if not user_id:
        messages.error(request, "Session expired. Please sign in or register.")
        return redirect('student_login')

    try:
        pending_user = User.objects.get(id=user_id)
        # Invalidate past OTPs
        EmailOTP.objects.filter(user=pending_user, is_used=False).update(is_used=True)
        # Generate new 6-digit OTP
        new_otp = f"{random.randint(100000, 999999):06d}"
        EmailOTP.objects.create(user=pending_user, otp_code=new_otp, purpose='registration')
        EmailMicroservice.send_otp_email(pending_user, new_otp)
        messages.success(request, f"A new 6-digit verification code was sent to {pending_user.email}!")
    except Exception as e:
        messages.error(request, f"Could not resend code: {e}")

    return redirect('verify_otp')

def verify_email(request, token):
    """
    Direct token link verification fallback.
    """
    try:
        username = TimestampSigner().unsign(token, max_age=86400)
        user = User.objects.get(username=username)
        user.is_active = True
        user.save()
        login(request, user)
        Notification.notify(user, f'Welcome, {user.first_name or user.username}!', 'Account verified! Explore listings or start selling.', 'welcome', 'fa-check-circle', '/profile/')
        messages.success(request, "Email verified successfully! Your account is now active.")
        return redirect('user_profile')
    except (BadSignature, SignatureExpired, User.DoesNotExist):
        messages.error(request, "Invalid or expired verification link.")
        return redirect('student_login')

def student_logout(request):
    """
    Logs out the current student user.
    """
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('home')

def user_profile(request):
    """
    Student profile view with user listings, orders, sales history, and listing creation.
    """
    u = request.user
    if request.method == 'POST' and u.is_authenticated:
        act, post = request.POST.get('action'), request.POST
        if act == 'update_profile':
            u.first_name = post.get('first_name', u.first_name)
            u.last_name = post.get('last_name', u.last_name)
            u.email = post.get('email', u.email)
            u.save()
            messages.success(request, "Profile updated successfully!")
        elif act == 'add_product' and post.get('name') and post.get('category') and post.get('price'):
            p = Product.objects.create(
                user=u,
                name=post['name'].strip(),
                category_id=post['category'],
                price=float(post['price']),
                stock=int(post.get('stock') or 1),
                description=post.get('description', '').strip(),
                product_image=request.FILES.get('product_image'),
                status=False,       # Hidden until admin approves
                is_approved=False   # Requires admin moderation
            )
            admin_url = request.build_absolute_uri('/admin/products/pendingproductreview/')
            EmailMicroservice.send_admin_new_pending_review_email(p, u, admin_url=admin_url)
            Notification.notify(u, f'Listing Submitted: {p.name}', f'Your item "{p.name}" is under review by college admin.', 'product_pending', 'fa-clock', '/profile/?tab=products')
            messages.success(request, f'Listing "{p.name}" submitted! It is under review by college admin and will appear publicly once approved.')
        elif act == 'edit_product':
            p = get_object_or_404(Product, id=post.get('product_id'))
            if p.user == u or u.is_superuser:
                p.name = post.get('name', p.name)
                p.price = float(post.get('price', p.price))
                p.stock = int(post.get('stock', p.stock))
                p.description = post.get('description', p.description)
                if post.get('category'):
                    p.category_id = post['category']
                if request.FILES.get('product_image'):
                    p.product_image = request.FILES['product_image']
                p.save()
                messages.success(request, f'"{p.name}" updated!')
        elif act == 'delete_product':
            p = get_object_or_404(Product, id=post.get('product_id'))
            if p.user == u or u.is_superuser:
                p.delete()
                messages.success(request, "Listing removed.")
        return redirect('user_profile')

    user_prods = Product.objects.filter(user=u).select_related('category').order_by('-created_at') if u.is_authenticated else Product.objects.select_related('category').all()[:6]
    user_orders = Order.objects.filter(user=u).prefetch_related('items').order_by('-created_at') if u.is_authenticated else []
    user_sales = OrderItem.objects.filter(product__user=u).select_related('order', 'product').order_by('-order__created_at') if u.is_authenticated else []
    user_blogs = BlogPost.objects.filter(author=u).select_related('category').order_by('-created_at') if u.is_authenticated else []
    
    return render(request, 'profile/profile.html', {
        'profile_user': u,
        'user_products': user_prods,
        'user_orders': user_orders,
        'user_sales': user_sales,
        'user_blogs': user_blogs,
        'categories': Category.objects.all()
    })
