import os, re
from django.utils import timezone
from django.db.models import Q
from products.models import Product, Category, Auction, ItemRequest, Order
from blog.models import Post
from sitesetting.models import Notification
from cart.models import CartItem
from cart.views import _get_or_create_cart

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class AgenticCommerceBot:
    @staticmethod
    def _prod_dict(p):
        return {
            'id': p.id,
            'name': p.name,
            'price': float(p.price),
            'formatted_price': f"Rs. {p.price:.2f}",
            'category': p.category.name if p.category else 'General',
            'image_url': p.product_image.url if p.product_image else '/static/images/default.jpg',
            'stock': p.stock,
            'url': f"/products/{p.id}/"
        }

    @staticmethod
    def _get_full_site_context(request):
        """Constructs rich real-time context of the entire Islington Marketplace."""
        recent_prods = Product.objects.filter(status=True, is_approved=True).select_related('category')[:12]
        prod_lines = [f"• Product #{p.id}: {p.name} | Rs. {p.price:.2f} | Category: {p.category.name if p.category else 'General'} | Stock: {p.stock}" for p in recent_prods]

        auctions = Auction.objects.filter(is_active=True, end_time__gt=timezone.now(), product__is_approved=True).select_related('product')[:4]
        auction_lines = [f"• Auction: {a.title} | Current Bid: Rs. {a.current_bid:.2f}" for a in auctions]

        wanted_reqs = ItemRequest.objects.filter(is_fulfilled=False)[:4]
        wanted_lines = [f"• Wanted: {r.title} | Budget: Rs. {r.budget:.2f} | Location: {r.preferred_location}" for r in wanted_reqs]

        cart = _get_or_create_cart(request)
        cart_items = [f"{i.quantity}x {i.product.name}" for i in cart.items.filter(is_active=True).select_related('product')]

        user = request.user if request.user.is_authenticated else None
        user_name = user.first_name or user.username if user else "Guest Student"

        context = f"""
--- ISLINGTON MARKETPLACE REAL-TIME DATABASE CONTEXT ---
Current User: {user_name} (Authenticated: {user is not None})
User Shopping Cart ({cart.total_items_count} items, Total: Rs. {cart.total_price:.2f}): {', '.join(cart_items) if cart_items else 'Empty'}

AVAILABLE PRODUCTS IN STORE:
{chr(10).join(prod_lines) if prod_lines else 'No items currently in stock.'}

ACTIVE 24-HOUR LIVE AUCTIONS:
{chr(10).join(auction_lines) if auction_lines else 'No active live auctions right now.'}

OPEN CAMPUS WANTED BOARD REQUESTS:
{chr(10).join(wanted_lines) if wanted_lines else 'No open wanted requests.'}

CAMPUS LOGISTICS & ESSENTIALS:
- Pickup Locations: Kumari Hall, Skill Block, Alumni Block, Nepal Block, Brit House, Himal Block, Main Block.
- Pickup Hours: 10:00 AM – 4:00 PM (Monday to Friday)
- Payment Gateways: Khalti Online Digital Wallet (Sandbox) & Cash on Delivery (COD)
- Support: info@islingtonmarket.np | +977-1-4412345
--------------------------------------------------------
"""
        return context

    @staticmethod
    def _gemini_generate(prompt: str, site_context: str) -> str:
        """Queries Google Gemini API (gemini-2.5-flash) for intelligent reasoned responses."""
        api_key = os.environ.get('GEMINI_API_KEY', '').strip()
        if not api_key:
            return None

        import requests
        models_to_try = ['gemini-2.5-flash', 'gemini-flash-latest', 'gemini-2.5-flash-lite']
        
        system_prompt = (
            "You are the official AI Agent & Reasoning Assistant for Islington Student Marketplace, "
            "a student-to-student e-commerce platform for Islington College in Kathmandu, Nepal. "
            "Your goal is to provide insightful, well-reasoned, friendly, and helpful responses to ANY user prompt—"
            "including product recommendations, pricing analysis, selling advice, campus logistics, study tips, and general conversation. "
            "Always explain your reasoning clearly and output clean Markdown text. "
            f"Use the following real-time marketplace database context to answer accurately:\n{site_context}\n\n"
            f"User Prompt: {prompt}"
        )

        for model_name in models_to_try:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
                payload = {
                    "contents": [
                        {
                            "role": "user",
                            "parts": [{"text": system_prompt}]
                        }
                    ]
                }
                res = requests.post(url, json=payload, timeout=12, verify=False)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get('candidates', [])
                    if candidates:
                        parts = candidates[0].get('content', {}).get('parts', [])
                        if parts:
                            return parts[0].get('text', '').strip()
            except Exception as e:
                print(f"Gemini API Error with {model_name}:", e)

        # Fallback to SDK if available
        if GEMINI_AVAILABLE:
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-2.5-flash')
                response = model.generate_content([system_prompt])
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                print("Gemini SDK Fallback Error:", e)

        return None

    @staticmethod
    def process_query(message: str, request) -> dict:
        msg, low, cart = message.strip(), message.strip().lower(), _get_or_create_cart(request)
        user = request.user if request.user.is_authenticated else None
        res = {
            'reply': '',
            'action_type': 'general',
            'products': [],
            'cart_data': {'count': cart.total_items_count, 'total': cart.total_price},
            'quick_replies': ['Explore Store', 'Active Auctions', 'My Cart']
        }

        # 1. Action Tool: Add to Cart
        if any(low.startswith(w) for w in ['add ', 'buy ']) or 'to cart' in low or 'add to bag' in low:
            target = re.sub(r'^(?:add|buy)\s+(?:the\s+)?', '', low)
            target = re.sub(r'\s+(?:to\s+(?:my\s+)?(?:cart|bag)|in\s+(?:my\s+)?(?:cart|bag)|now)$', '', target).strip()
            p = Product.objects.filter(status=True, is_approved=True).filter(
                Q(name__icontains=target) | Q(description__icontains=target) | Q(category__name__icontains=target)
            ).first() if target else None

            if not p:
                res.update({'reply': f"I couldn't find a product matching '{target}'. Try another keyword or browse categories."})
            elif user and p.user == user:
                res.update({'reply': f"You cannot add **{p.name}** because you listed it yourself!", 'products': [AgenticCommerceBot._prod_dict(p)]})
            elif p.stock <= 0:
                res.update({'reply': f"Sorry, **{p.name}** is currently out of stock.", 'products': [AgenticCommerceBot._prod_dict(p)]})
            else:
                it, created = CartItem.objects.get_or_create(cart=cart, product=p)
                if not created:
                    it.quantity = min(it.quantity + 1, p.stock or 1)
                    it.save()
                res.update({
                    'reply': f"Added **{p.name}** (Rs. {p.price:.2f}) directly to your cart!",
                    'action_type': 'cart_updated',
                    'products': [AgenticCommerceBot._prod_dict(p)],
                    'cart_data': {'count': cart.total_items_count, 'total': cart.total_price},
                    'quick_replies': ['Proceed to Checkout', 'View Cart', 'Continue Shopping']
                })
            return res

        # 2. Action Tool: View Cart / Cart Summary
        if any(w in low for w in ['show cart', 'view cart', 'my cart', 'check cart', 'cart summary', 'what is in my cart', 'open cart']):
            items = cart.items.filter(is_active=True).select_related('product')
            if not items.exists():
                res.update({'reply': "Your cart is currently empty. What would you like to shop for today?", 'action_type': 'cart_summary'})
            else:
                lines = [f"• **{it.quantity}x {it.product.name}** — Rs. {it.sub_total:.2f}" for it in items]
                res.update({
                    'reply': f"Here is your cart (**{cart.total_items_count} items**):\n\n" + "\n".join(lines) + f"\n\n**Total: Rs. {cart.total_price:.2f}**",
                    'action_type': 'cart_summary',
                    'products': [AgenticCommerceBot._prod_dict(i.product) for i in items],
                    'quick_replies': ['Proceed to Checkout', 'Clear Cart', 'Continue Shopping']
                })
            return res

        # 3. Action Tool: Clear Cart
        if any(w in low for w in ['clear cart', 'empty cart', 'clear my cart', 'delete cart']):
            cart.items.all().delete()
            res.update({'reply': "Your shopping cart has been cleared.", 'action_type': 'cart_cleared', 'cart_data': {'count': 0, 'total': 0.0}})
            return res

        # 4. Action Tool: Checkout Redirect
        if any(w in low for w in ['checkout', 'proceed to pay', 'buy all', 'place order', 'go to checkout']):
            if cart.total_items_count == 0:
                res.update({'reply': "Your cart is empty! Add products first."})
            else:
                res.update({
                    'reply': f"You have **{cart.total_items_count} item(s)** totaling **Rs. {cart.total_price:.2f}** ready for checkout.",
                    'action_type': 'checkout_redirect',
                    'redirect_url': '/checkout/',
                    'quick_replies': ['View Cart', 'Continue Shopping']
                })
            return res

        # 5. Action Tool: Post Wanted Request
        if any(w in low for w in ['post wanted', 'create wanted', 'add wanted', 'wanted request']) or ('post ' in low and 'wanted' in low):
            if not user:
                res.update({'reply': "Please **Sign In** to post a request on the Campus Wanted Board."})
                return res

            b_match = re.search(r'(?:budget|rs\.?|npr|for|of|price|cost|under)\s*(?:of\s*)?(?:rs\.?|npr)?\s*(\d+(?:\.\d+)?)', msg, re.I)
            b_amt = float(b_match.group(1)) if b_match else 0.0

            t_clean = msg
            t_clean = re.sub(r'^(?:post|create|add|need|looking for)?\s*(?:a\s+)?(?:wanted\s+)?(?:request\s+)?(?:for\s+)?(?:of\s+)?', '', t_clean, flags=re.I)
            t_clean = re.sub(r'(?:with\s+)?(?:a\s+)?(?:budget|rs\.?|npr|for|of|price|cost|under)\s*(?:of\s*)?(?:rs\.?|npr)?\s*\d+.*$', '', t_clean, flags=re.I).strip()
            t_clean = re.sub(r'\s+', ' ', t_clean).strip()

            if len(t_clean) >= 2:
                ItemRequest.objects.create(user=user, title=t_clean.title(), budget=b_amt, urgency='today', preferred_location='Kumari Hall', description='Posted via AI Assistant')
                Notification.notify_all(f"📢 Wanted: {t_clean[:25]}", f"{user.username} needs this! Rs. {b_amt:.2f}", 'item_wanted', 'fa-bullhorn', '/#wantedBoardSection', exclude_user=user)
                res.update({'reply': f"Posted request for **{t_clean.title()}** with budget **Rs. {b_amt:.2f}** to the Campus Wanted Board! Peers have been notified."})

        # 6. Greetings & General Chat Check
        greetings = ['hi', 'hello', 'hey', 'greetings', 'namaste', 'good morning', 'good afternoon', 'good evening', 'who are you', 'what can you do', 'help']
        is_greeting = any(low == g or low.startswith(g + ' ') or low.endswith(' ' + g) for g in greetings)

        # 7. Database Product Lookup for Card Attachments (Only if user is searching for products!)
        prod_dicts = []
        if not is_greeting and len(low) >= 3:
            qs = Product.objects.filter(status=True, is_approved=True).select_related('category', 'user')
            u_match = re.search(r'(?:under|below|less than|budget of|max(?:imum)?|upto)\s+(?:rs\.?|npr)?\s*(\d+)', low)
            max_p = float(u_match.group(1)) if u_match else None
            if max_p:
                qs = qs.filter(price__lte=max_p)

            cat_match = next((c for c in Category.objects.all() if c.name.lower() in low and len(c.name) > 3), None)
            if cat_match:
                qs = qs.filter(category=cat_match)

            clean_q = re.sub(r'\b(find|search|show|me|get|give|looking|for|a|an|the|some|good|best|cheap|cheapest|items|products|under|below|less|than|rs|npr|please|can|you|is|there|any)\b', ' ', low)
            if max_p: clean_q = clean_q.replace(str(int(max_p)), ' ')
            clean_q = re.sub(r'\s+', ' ', clean_q).strip()

            if clean_q and len(clean_q) >= 2:
                f_qs = qs.filter(Q(name__icontains=clean_q) | Q(description__icontains=clean_q))
                if f_qs.exists():
                    prod_dicts = [AgenticCommerceBot._prod_dict(p) for p in f_qs[:6]]
            elif max_p or cat_match:
                prod_dicts = [AgenticCommerceBot._prod_dict(p) for p in qs[:6]]

        # 8. Generate Response using Gemini 1.5 Flash with Full Site Context
        site_context = AgenticCommerceBot._get_full_site_context(request)
        ai_reply = AgenticCommerceBot._gemini_generate(msg, site_context)

        if ai_reply:
            first_n = prod_dicts[0]['name'] if prod_dicts else "Items"
            res.update({
                'reply': ai_reply,
                'action_type': 'product_list' if prod_dicts else 'general',
                'products': prod_dicts,
                'quick_replies': [f"Add {first_n[:18]} to cart", 'View Cart', 'Checkout'] if prod_dicts else ['Explore Store', 'Active Auctions', 'My Cart']
            })
            return res

        # 9. Intelligent Fallback if Gemini API key is missing or unreachable
        if is_greeting:
            res.update({
                'reply': "Hello! 👋 I am your **Islington AI Assistant**. I can help you search campus items, check out 24-hour live auctions, post wanted board requests, or manage your shopping cart. What are you looking for today?",
                'quick_replies': ['Explore Store', 'Active Auctions', 'My Cart']
            })
        elif prod_dicts:
            first_n = prod_dicts[0]['name']
            res.update({
                'reply': f"Found **{len(prod_dicts)} item(s)** matching your search:",
                'action_type': 'product_list',
                'products': prod_dicts,
                'quick_replies': [f"Add {first_n[:18]} to cart", 'View Cart', 'Checkout']
            })
        else:
            res.update({
                'reply': "I couldn't find any specific products matching that in our store, but feel free to ask me anything about campus trade, wanted requests, or orders!",
                'quick_replies': ['Explore Store', 'Active Auctions', 'My Cart']
            })

        return res
