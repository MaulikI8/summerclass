from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from products.models import Product, Category as ProductCategory
from blog.models import Post
from sitesetting.models import Banner, Notification
from utils.email_microservice import EmailMicroservice

def home(request):
    banners = Banner.objects.filter(is_active=True).order_by('order', '-created_at')
    products = Product.objects.select_related('category').filter(status=True).order_by('-created_at')
    if not products.exists():
        products = Product.objects.select_related('category').all().order_by('-created_at')
    blogs = Post.objects.select_related('category').filter(status=True).order_by('-created_at')[:3]
    return render(request, 'home/home1.html', {
        'banners': banners,
        'products': products,
        'featured_products': products[:8],
        'categories': ProductCategory.objects.all(),
        'blogs': blogs,
        'latest_blogs': blogs,
        'total_products': Product.objects.count(),
        'total_categories': ProductCategory.objects.count(),
        'total_blogs': Post.objects.count(),
    })

def user_profile(request):
    user = request.user
    categories = ProductCategory.objects.all()
    user_products = Product.objects.filter(user=user).select_related('category').order_by('-created_at') if user.is_authenticated else Product.objects.select_related('category').all()[:6]
    
    if request.method == 'POST' and user.is_authenticated:
        act = request.POST.get('action')
        if act == 'update_profile':
            user.first_name, user.last_name, user.email = request.POST.get('first_name', user.first_name), request.POST.get('last_name', user.last_name), request.POST.get('email', user.email)
            user.save()
            messages.success(request, "Profile updated successfully!")

        elif act == 'add_product':
            name, cat_id, price = request.POST.get('name', '').strip(), request.POST.get('category'), request.POST.get('price')
            if name and cat_id and price:
                p = Product.objects.create(
                    user=user, name=name, category=ProductCategory.objects.get(id=cat_id),
                    price=float(price), stock=int(request.POST.get('stock') or 1),
                    description=request.POST.get('description', '').strip(),
                    product_image=request.FILES.get('product_image'), status=True
                )
                Notification.notify(user, f'Your listing "{p.name}" is now live!', f'Listed for Rs. {p.price}.', 'product_listed', 'fa-check-circle', f'/products/{p.id}/')
                Notification.notify_all(f'New on Marketplace: {p.name}', f'{user.first_name or user.username} listed "{p.name}" for Rs. {p.price}.', 'product_listed', 'fa-box-open', f'/products/{p.id}/', exclude_user=user)
                EmailMicroservice.send_product_listed_email(user, p)
                messages.success(request, f'"{p.name}" published successfully!')
            else:
                messages.error(request, "Please fill in all required fields.")

        elif act == 'edit_product':
            p = get_object_or_404(Product, id=request.POST.get('product_id'))
            if p.user == user or user.is_superuser:
                p.name, p.price = request.POST.get('name', p.name), float(request.POST.get('price', p.price))
                p.stock, p.description = int(request.POST.get('stock', p.stock)), request.POST.get('description', p.description)
                if request.POST.get('category'): p.category = ProductCategory.objects.get(id=request.POST.get('category'))
                if request.FILES.get('product_image'): p.product_image = request.FILES.get('product_image')
                p.save()
                messages.success(request, f'"{p.name}" updated successfully!')

        elif act == 'delete_product':
            p = get_object_or_404(Product, id=request.POST.get('product_id'))
            if p.user == user or user.is_superuser:
                name = p.name; p.delete()
                messages.success(request, f'"{name}" removed.')

        return redirect('user_profile')

    return render(request, 'profile/profile.html', {'profile_user': user, 'user_products': user_products, 'categories': categories})

def student_login(request):
    if request.user.is_authenticated: return redirect('user_profile')
    if request.method == 'POST':
        user = authenticate(request, username=request.POST.get('username', '').strip(), password=request.POST.get('password', ''))
        if user:
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            return redirect('user_profile')
        messages.error(request, "Invalid student username or password.")
    return render(request, 'profile/login.html')

def student_register(request):
    if request.user.is_authenticated: return redirect('user_profile')
    if request.method == 'POST':
        u, em, pw, cpw = request.POST.get('username', '').strip(), request.POST.get('email', '').strip(), request.POST.get('password', ''), request.POST.get('confirm_password', '')
        if not u or not em or not pw: messages.error(request, "Please fill in all required fields.")
        elif pw != cpw: messages.error(request, "Passwords do not match.")
        elif User.objects.filter(username=u).exists(): messages.error(request, "Username is already taken.")
        elif User.objects.filter(email=em).exists(): messages.error(request, "An account with this email already exists.")
        else:
            user = User.objects.create_user(username=u, email=em, password=pw, first_name=request.POST.get('first_name', '').strip(), last_name=request.POST.get('last_name', '').strip())
            login(request, user)
            Notification.notify(user, f'Welcome, {user.first_name or user.username}!', 'Explore listings or post your first product to start selling.', 'welcome', 'fa-hand-wave', '/profile/?tab=add')
            EmailMicroservice.send_welcome_email(user)
            messages.success(request, f"Welcome to Islington Marketplace, {user.first_name or user.username}!")
            return redirect('user_profile')
    return render(request, 'profile/register.html')

def student_logout(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect('home')

def custom_404(request, exception=None):
    return render(request, '404.html', status=404)
