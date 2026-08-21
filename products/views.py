from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from .models import Category, Product, TradeOffer, Wishlist, ItemRequest
from sitesetting.models import Notification

def products(request):
    q, cat = request.GET.get('q', '').strip(), request.GET.get('category', '').strip()
    qs = Product.objects.select_related('category', 'user').filter(status=True, is_approved=True).order_by('-created_at')
    if q: qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q) | Q(category__name__icontains=q) | Q(user__username__icontains=q))
    if cat and cat != 'All Categories': qs = qs.filter(category__name__icontains=cat)
    wish_ids = set(Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True)) if request.user.is_authenticated else set()
    return render(request, 'products/products.html', {
        'products': qs, 'categories': Category.objects.all(), 'query': q, 'selected_category': cat, 'total_count': qs.count(), 'wishlist_ids': wish_ids
    })

def product_detail(request, id):
    p = get_object_or_404(Product.objects.select_related('category', 'user'), pk=id)
    if not p.is_approved and not (request.user.is_authenticated and (request.user == p.user or request.user.is_staff or request.user.is_superuser)):
        p = get_object_or_404(Product, pk=id, is_approved=True, status=True)
    is_wishlisted = Wishlist.objects.filter(user=request.user, product=p).exists() if request.user.is_authenticated else False
    return render(request, 'products/product_detail.html', {
        'product': p,
        'related_products': Product.objects.select_related('user').filter(category=p.category, is_approved=True, status=True).exclude(pk=id)[:4],
        'is_wishlisted': is_wishlisted
    })

def search_suggest(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 2: return JsonResponse({'results': []})
    qs = Product.objects.select_related('category').filter(
        Q(name__icontains=q) | Q(category__name__icontains=q) | Q(description__icontains=q),
        status=True, is_approved=True
    )[:6]
    results = [{
        'id': p.id,
        'name': p.name,
        'price': f"{p.price:.2f}",
        'category': p.category.name,
        'image': p.product_image.url if p.product_image else '/static/images/default.jpg',
        'url': f"/products/{p.id}/"
    } for p in qs]
    return JsonResponse({'results': results})

@login_required
def toggle_wishlist(request, id):
    p = get_object_or_404(Product, pk=id, status=True, is_approved=True)
    item, created = Wishlist.objects.get_or_create(user=request.user, product=p)
    if not created:
        item.delete()
        action = 'removed'
    else:
        action = 'added'
    count = Wishlist.objects.filter(user=request.user).count()
    return JsonResponse({'status': 'ok', 'action': action, 'count': count, 'product_id': p.id})

@login_required
def send_offer(request, id):
    p = get_object_or_404(Product.objects.select_related('user'), pk=id)
    if p.user == request.user:
        messages.error(request, "You cannot make an offer on your own listing.")
        return redirect('product_detail', id=id)
    if request.method == 'POST' and p.user:
        off_type = request.POST.get('offer_type', 'price')
        price_val = float(request.POST['offered_price']) if request.POST.get('offered_price') else None
        desc = request.POST.get('trade_item_desc', '').strip()
        offer = TradeOffer.objects.create(product=p, sender=request.user, receiver=p.user, offer_type=off_type, offered_price=price_val, trade_item_desc=desc)
        title_text = f"Offer Rs. {price_val:.2f}" if off_type == 'price' else "Trade Swap Offer"
        Notification.notify(p.user, f"New {title_text} on '{p.name[:25]}'", f"{request.user.username} sent an offer for your item.", 'trade_offer', 'fa-handshake', '/profile/?tab=recvreq')
        messages.success(request, f"Your {offer.get_offer_type_display()} has been sent to seller {p.user.username}!")
    return redirect('product_detail', id=id)

@login_required
def respond_offer(request, offer_id, action):
    offer = get_object_or_404(TradeOffer.objects.select_related('sender', 'product'), pk=offer_id, receiver=request.user)
    if action in ('accept', 'decline'):
        offer.status = 'accepted' if action == 'accept' else 'declined'
        offer.save()
        status_word = 'Accepted' if action == 'accept' else 'Declined'
        Notification.notify(offer.sender, f"Offer {status_word}: {offer.product.name}", f"The seller {request.user.username} {action}ed your offer.", 'trade_update', 'fa-handshake', '/profile/?tab=sentreq')
        messages.success(request, f"Offer marked as {status_word}.")
    return redirect('/profile/?tab=recvreq')

@login_required
def post_item_request(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        budget = float(request.POST.get('budget', 0) or 0)
        urgency = request.POST.get('urgency', 'today')
        loc = request.POST.get('preferred_location', 'Kumari Hall').strip()
        phone = request.POST.get('contact_phone', '').strip()
        desc = request.POST.get('description', '').strip()
        cat_id = request.POST.get('category')
        cat = Category.objects.filter(id=cat_id).first() if cat_id else None
        if title:
            ItemRequest.objects.create(user=request.user, title=title, category=cat, budget=budget, urgency=urgency, preferred_location=loc, contact_phone=phone, description=desc)
            Notification.notify_all(f"📢 Wanted: {title[:25]}", f"{request.user.username} is looking for this! Budget: Rs. {budget:.2f}", 'item_wanted', 'fa-bullhorn', '/#wantedBoardSection', exclude_user=request.user)
            messages.success(request, f"Your wanted request for '{title}' has been posted!")
    return redirect('/#wantedBoardSection')

@login_required
def fulfill_item_request(request, request_id):
    req = get_object_or_404(ItemRequest.objects.select_related('user'), id=request_id, is_fulfilled=False)
    if req.user == request.user:
        messages.error(request, "You cannot fulfill your own wanted request.")
        return redirect('/#wantedBoardSection')
    req.is_fulfilled, req.fulfilled_by = True, request.user
    req.save()
    Notification.notify(req.user, f"Match Found for '{req.title[:25]}'!", f"Student {request.user.username} says they have this item! Meetup spot: {req.preferred_location}.", 'wanted_match', 'fa-handshake', '/profile/?tab=recvreq')
    messages.success(request, f"Awesome! We notified {req.user.username} that you have '{req.title}'.")
    return redirect('/#wantedBoardSection')

@login_required
def delete_item_request(request, request_id):
    req = get_object_or_404(ItemRequest, id=request_id, user=request.user)
    req.delete()
    messages.success(request, "Item request removed.")
    return redirect('/#wantedBoardSection')

@login_required
def delete_product_view(request, id):
    p = get_object_or_404(Product, id=id)
    if p.user == request.user or request.user.is_staff or request.user.is_superuser:
        p_name = p.name
        p.delete()
        messages.success(request, f'Listing "{p_name}" removed successfully.')
        return redirect('user_profile')
    messages.error(request, "You do not have permission to delete this listing.")
    return redirect('product_detail', id=id)