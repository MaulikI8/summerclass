from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.utils.timesince import timesince
from products.models import Product, Category as ProductCategory
from blog.models import Post, Category as BlogCategory
from pages.models import Page
from sitesetting.models import SiteSetting, Banner, Notification
from utils.email_microservice import EmailMicroservice

def home(request):
    banners = Banner.objects.filter(is_active=True).order_by('order', '-created_at')
    products = Product.objects.select_related('category').filter(status=True).order_by('-created_at')
    if not products.exists():
        products = Product.objects.select_related('category').all().order_by('-created_at')
    categories = ProductCategory.objects.all()
    blogs = Post.objects.select_related('category').filter(status=True).order_by('-created_at')
    if not blogs.exists():
        blogs = Post.objects.select_related('category').all().order_by('-created_at')
    
    featured_products = products.filter(status=True)[:8]
    if not featured_products.exists():
        featured_products = products[:8]
        
    latest_blogs = blogs[:3]
    total_products = Product.objects.count()
    total_categories = ProductCategory.objects.count()
    total_blogs = Post.objects.count()

    return render(request, 'home/home1.html', {
        'banners': banners,
        'products': products,
        'featured_products': featured_products,
        'categories': categories,
        'blogs': blogs,
        'latest_blogs': latest_blogs,
        'total_products': total_products,
        'total_categories': total_categories,
        'total_blogs': total_blogs,
    })

def user_profile(request):
    user = request.user
    categories = ProductCategory.objects.all()
    
    if user.is_authenticated:
        user_products = Product.objects.filter(user=user).select_related('category').order_by('-created_at')
    else:
        user_products = Product.objects.select_related('category').all()[:6]
    
    if request.method == 'POST' and user.is_authenticated:
        action = request.POST.get('action')

        # 1. Update Profile Action
        if action == 'update_profile':
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            email = request.POST.get('email')
            if first_name is not None:
                user.first_name = first_name
            if last_name is not None:
                user.last_name = last_name
            if email:
                user.email = email
            user.save()
            messages.success(request, "Your student profile has been successfully updated!")
            return redirect('user_profile')

        # 2. Add New Product Listing Action
        elif action == 'add_product':
            name = request.POST.get('name', '').strip()
            category_id = request.POST.get('category')
            price = request.POST.get('price')
            stock = request.POST.get('stock', 1)
            description = request.POST.get('description', '').strip()
            product_image = request.FILES.get('product_image')

            if not name or not category_id or not price:
                messages.error(request, "Please fill in all required fields (Title, Category, Price).")
            else:
                try:
                    category = ProductCategory.objects.get(id=category_id)
                    new_product = Product.objects.create(
                        user=user,
                        name=name,
                        category=category,
                        price=float(price),
                        stock=int(stock) if stock else 1,
                        description=description,
                        product_image=product_image,
                        status=True
                    )
                    # Notify the seller
                    Notification.notify(
                        recipient=user,
                        title=f'Your listing "{new_product.name}" is now live!',
                        message=f'Your product has been published to the marketplace at Rs. {new_product.price}.',
                        notif_type='product_listed',
                        icon='fa-check-circle',
                        link=f'/products/{new_product.id}/',
                    )
                    # Notify all other users about the new listing
                    Notification.notify_all(
                        title=f'New on Marketplace: {new_product.name}',
                        message=f'{user.first_name or user.username} just listed "{new_product.name}" for Rs. {new_product.price}.',
                        notif_type='product_listed',
                        icon='fa-box-open',
                        link=f'/products/{new_product.id}/',
                        exclude_user=user,
                    )
                    # Trigger Email Microservice (Async)
                    EmailMicroservice.send_product_listed_email(user, new_product)
                    messages.success(request, f'"{new_product.name}" was successfully published to the marketplace!')
                    return redirect('user_profile')
                except Exception as e:
                    messages.error(request, f"Error creating product: {str(e)}")

        # 3. Edit Product Listing Action
        elif action == 'edit_product':
            product_id = request.POST.get('product_id')
            product = get_object_or_404(Product, id=product_id)
            if product.user == user or user.is_superuser:
                product.name = request.POST.get('name', product.name)
                category_id = request.POST.get('category')
                if category_id:
                    product.category = ProductCategory.objects.get(id=category_id)
                product.price = float(request.POST.get('price', product.price))
                product.stock = int(request.POST.get('stock', product.stock))
                product.description = request.POST.get('description', product.description)
                if request.FILES.get('product_image'):
                    product.product_image = request.FILES.get('product_image')
                product.save()
                messages.success(request, f'"{product.name}" has been updated!')
            else:
                messages.error(request, "You do not have permission to edit this product.")
            return redirect('user_profile')

        # 4. Delete Product Listing Action
        elif action == 'delete_product':
            product_id = request.POST.get('product_id')
            product = get_object_or_404(Product, id=product_id)
            if product.user == user or user.is_superuser:
                prod_name = product.name
                product.delete()
                messages.success(request, f'"{prod_name}" was successfully removed.')
            else:
                messages.error(request, "You do not have permission to delete this product.")
            return redirect('user_profile')

    return render(request, 'profile/profile.html', {
        'profile_user': user,
        'user_products': user_products,
        'categories': categories,
    })

def student_login(request):
    if request.user.is_authenticated:
        return redirect('user_profile')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            return redirect('user_profile')
        else:
            messages.error(request, "Invalid student username or password.")

    return render(request, 'profile/login.html')

def student_register(request):
    if request.user.is_authenticated:
        return redirect('user_profile')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not username or not email or not password:
            messages.error(request, "Please fill in all required fields.")
        elif password != confirm_password:
            messages.error(request, "Passwords do not match.")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "Username is already taken. Please choose another.")
        elif User.objects.filter(email=email).exists():
            messages.error(request, "An account with this college email already exists.")
        else:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            login(request, user)
            # Welcome notification
            Notification.notify(
                recipient=user,
                title=f'Welcome to Islington Marketplace, {user.first_name or user.username}!',
                message='Start by browsing listings or post your first product to start selling on campus.',
                notif_type='welcome',
                icon='fa-hand-wave',
                link='/profile/?tab=add',
            )
            # Trigger Email Microservice (Async)
            EmailMicroservice.send_welcome_email(user)
            messages.success(request, f"Welcome to Islington Marketplace, {user.first_name or user.username}!")
            return redirect('user_profile')

    return render(request, 'profile/register.html')

def student_logout(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect('home')


# ========================= NOTIFICATION API ENDPOINTS =========================

@require_GET
def api_notifications(request):
    """JSON endpoint for AJAX polling — returns unread count and recent notifications."""
    if not request.user.is_authenticated:
        return JsonResponse({'unread_count': 0, 'notifications': []})

    notifications = Notification.objects.filter(
        recipient=request.user
    ).order_by('-created_at')[:20]

    unread_count = Notification.objects.filter(
        recipient=request.user, is_read=False
    ).count()

    notif_list = []
    for n in notifications:
        notif_list.append({
            'id': n.id,
            'type': n.notif_type,
            'title': n.title,
            'message': n.message,
            'icon': n.icon,
            'link': n.link,
            'is_read': n.is_read,
            'time_ago': timesince(n.created_at) + ' ago',
            'sender': n.sender.get_full_name() if n.sender else '',
        })

    return JsonResponse({
        'unread_count': unread_count,
        'notifications': notif_list,
    })


@require_POST
def api_notification_read(request):
    """Mark a single notification as read."""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error'}, status=401)

    notif_id = request.POST.get('id')
    if notif_id:
        Notification.objects.filter(
            id=notif_id, recipient=request.user
        ).update(is_read=True)

    return JsonResponse({'status': 'ok'})


@require_POST
def api_notification_read_all(request):
    """Mark ALL notifications as read for the current user."""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error'}, status=401)

    Notification.objects.filter(
        recipient=request.user, is_read=False
    ).update(is_read=True)

    return JsonResponse({'status': 'ok'})


def custom_404(request, exception=None):
    return render(request, '404.html', status=404)
