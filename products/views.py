from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from .models import Category, Product, TradeOffer, Wishlist, ItemRequest, SearchHistory
from sitesetting.models import Notification

def products(request):
    q, cat = request.GET.get('q', '').strip(), request.GET.get('category', '').strip()
    qs = list(Product.objects.select_related('category', 'user').filter(status=True, is_approved=True).order_by('-created_at'))
    
    if q:
        # Filter matching candidates
        filtered = [p for p in qs if q.lower() in p.name.lower() or q.lower() in (p.description or '').lower() or q.lower() in (p.category.name if p.category else '').lower() or q.lower() in (p.user.username if p.user else '').lower()]
        
        # Log search history
        try:
            if not request.session.session_key:
                request.session.create()
            SearchHistory.objects.create(
                user=request.user if request.user.is_authenticated else None,
                session_key=request.session.session_key,
                query=q
            )
        except Exception:
            pass

        # TF-IDF Smart Search Ranking (Week 10 V2)
        if filtered:
            try:
                from sklearn.feature_extraction.text import TfidfVectorizer
                from sklearn.metrics.pairwise import cosine_similarity

                docs = [f"{p.name} {p.description or ''} {p.category.name if p.category else ''}" for p in filtered]
                vec = TfidfVectorizer(stop_words='english')
                p_matrix = vec.fit_transform(docs)
                q_vec = vec.transform([q])
                sims = cosine_similarity(q_vec, p_matrix)[0]

                for idx, p in enumerate(filtered):
                    score = float(sims[idx])
                    p.match_score = score
                    p.match_percentage = f"{int(round(score * 100))}% Match" if score > 0 else None

                filtered.sort(key=lambda item: getattr(item, 'match_score', 0), reverse=True)
            except Exception:
                pass
        qs = filtered

    if cat and cat != 'All Categories':
        qs = [p for p in qs if p.category and cat.lower() in p.category.name.lower()]

    wish_ids = set(Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True)) if request.user.is_authenticated else set()
    return render(request, 'products/products.html', {
        'products': qs, 'categories': Category.objects.all(), 'query': q, 'selected_category': cat, 'total_count': len(qs), 'wishlist_ids': wish_ids
    })

def ai_product_finder(request):
    """
    AI Product Finder (Requirement-based recommendation + Budget filtering + TF-IDF ranking)
    Per Week 10 Tutorial V2 specification.
    """
    req = request.GET.get('requirement', '').strip()
    budget_raw = request.GET.get('max_budget', '').strip()
    max_budget = None
    if budget_raw:
        try:
            max_budget = float(budget_raw)
        except ValueError:
            max_budget = None

    candidates = Product.objects.select_related('category', 'user').filter(status=True, is_approved=True, stock__gt=0)
    
    # 1. Deterministic Rule First: Budget Filtering
    if max_budget is not None and max_budget > 0:
        candidates = candidates.filter(price__lte=max_budget)

    candidates = list(candidates)
    results = []

    # 2. ML Ranking Second: TF-IDF + Cosine Similarity
    if req and candidates:
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity

            docs = [f"{p.name} {p.description or ''} {p.category.name if p.category else ''}" for p in candidates]
            vec = TfidfVectorizer(stop_words='english')
            p_matrix = vec.fit_transform(docs)
            q_vec = vec.transform([req])
            sims = cosine_similarity(q_vec, p_matrix)[0]

            for idx, p in enumerate(candidates):
                score = float(sims[idx])
                if score > 0:
                    p.match_score = score
                    p.match_percentage = f"{int(round(score * 100))}% Match"
                    results.append(p)

            results.sort(key=lambda item: getattr(item, 'match_score', 0), reverse=True)
        except Exception:
            results = candidates
    elif max_budget is not None:
        results = candidates

    return render(request, 'products/product_finder.html', {
        'results': results,
        'requirement': req,
        'max_budget': max_budget,
        'total_count': len(results),
        'categories': Category.objects.all()
    })


def product_detail(request, id):
    try:
        p = Product.objects.select_related('category', 'user').get(pk=id)
    except Exception:
        return render(request, '404.html', status=404)

    if not p.is_approved and not (request.user.is_authenticated and (request.user == p.user or request.user.is_staff or request.user.is_superuser)):
        return render(request, '404.html', status=404)

    is_wishlisted = False
    if request.user.is_authenticated:
        try:
            is_wishlisted = Wishlist.objects.filter(user=request.user, product=p).exists()
        except Exception:
            pass

    in_cart = False
    try:
        from cart.models import CartItem
        if request.user.is_authenticated:
            in_cart = CartItem.objects.filter(cart__user=request.user, product=p, is_active=True).exists()
        elif request.session.session_key:
            in_cart = CartItem.objects.filter(cart__cart_id=request.session.session_key, product=p, is_active=True).exists()
    except Exception:
        pass

    # Track view with 30-min deduplication
    ai_recommendations = []
    try:
        from .recommendations import HybridRecommender
        HybridRecommender.track_view(request, p)
        recommender = HybridRecommender(request)
        ai_recommendations = recommender.recommend(current_product=p, limit=4)
    except Exception:
        ai_recommendations = []

    reviews = []
    user_review = None
    try:
        reviews = list(Review.objects.filter(product=p, status=True).select_related('user').order_by('-created_at'))
        if request.user.is_authenticated:
            user_review = next((r for r in reviews if r.user_id == request.user.id), None)
    except Exception:
        pass

    related_products = []
    try:
        if p.category:
            related_products = list(Product.objects.select_related('user').filter(category=p.category, is_approved=True, status=True).exclude(pk=id)[:4])
    except Exception:
        pass

    return render(request, 'products/product_detail.html', {
        'product': p,
        'related_products': related_products,
        'ai_recommendations': ai_recommendations,
        'is_wishlisted': is_wishlisted,
        'in_cart': in_cart,
        'reviews': reviews,
        'user_review': user_review
    })

@login_required
def submit_review(request, id):
    p = get_object_or_404(Product, pk=id, status=True, is_approved=True)
    if request.method == 'POST':
        rating = int(request.POST.get('rating', 5))
        rating = max(1, min(5, rating))
        comment = request.POST.get('comment', '').strip()
        Review.objects.update_or_create(
            user=request.user, product=p,
            defaults={'rating': rating, 'comment': comment, 'status': True}
        )
        messages.success(request, "Thank you for your rating & review!")
    return redirect('product_detail', id=id)


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