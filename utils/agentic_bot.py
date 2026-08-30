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
    def _gemini_generate(prompt: str, context_info: str) -> str:
        """Query Google Gemini API (gemini-1.5-flash) for AI response generation."""
        api_key = os.environ.get('GEMINI_API_KEY', '').strip()
        if not api_key or not GEMINI_AVAILABLE:
            return None

        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            system_instruction = (
                "You are the official AI Commerce Assistant for Islington Student Marketplace, "
                "an e-commerce marketplace for Islington College students in Kathmandu, Nepal. "
                "Be helpful, concise, friendly, and output clean markdown text. "
                "Use the following real-time database context to answer the user's question accurately:\n\n"
                f"{context_info}"
            )
            response = model.generate_content([system_instruction, f"User Query: {prompt}"])
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            print("Gemini API Error:", e)

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

        # 1. Add to Cart (Deterministic Action Tool)
        if any(low.startswith(w) for w in ['add ', 'buy ']) or 'to cart' in low:
            target = re.sub(r'^(?:add|buy)\s+(?:the\s+)?', '', low)
            target = re.sub(r'\s+(?:to\s+(?:my\s+)?cart|in\s+(?:my\s+)?cart|now)$', '', target).strip()
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

        # 2. View Cart / Summary
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

        # 3. Clear Cart
        if any(w in low for w in ['clear cart', 'empty cart', 'clear my cart', 'delete cart']):
            cart.items.all().delete()
            res.update({'reply': "Your shopping cart has been cleared.", 'action_type': 'cart_cleared', 'cart_data': {'count': 0, 'total': 0.0}})
            return res

        # 4. Checkout
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

        # 5. Live Auctions
        if any(w in low for w in ['auction', 'bid', 'bidding', 'flash auction', 'ending soon']):
            auctions = list(Auction.objects.filter(is_active=True, end_time__gt=timezone.now(), product__is_approved=True).select_related('product')[:4])
            if not auctions:
                res.update({'reply': "No active live auctions right now. Browse store listings or post an auction from your profile!"})
            else:
                lines = ["Here are the **24-Hour Live Auctions** active right now:"]
                for a in auctions:
                    rem = a.end_time - timezone.now()
                    lines.append(f"• **{a.title}** (Current Bid: **Rs. {a.current_bid:.2f}** • Ends in: **{int(rem.total_seconds()//3600)}h {int((rem.total_seconds()%3600)//60)}m**)")
                res.update({
                    'reply': "\n\n".join(lines),
                    'action_type': 'auction_list',
                    'products': [AgenticCommerceBot._prod_dict(a.product) for a in auctions if a.product],
                    'quick_replies': ['Explore Store', 'My Cart']
                })
            return res

        # 6. Wanted Board (Query / Post)
        if any(w in low for w in ['wanted', 'looking for', 'need book', 'need kit', 'item request']):
            if any(w in low for w in ['post', 'create', 'add']) and len(low) > 8:
                if not user:
                    res.update({'reply': "Please **Sign In** to post a request on the Campus Wanted Board."})
                    return res
                b_match = re.search(r'(?:budget|rs\.?|for)\s*(\d+)', msg, re.I)
                b_amt = float(b_match.group(1)) if b_match else 0.0
                t_clean = re.sub(r'^(?:post|create|add)?\s*(?:a\s+)?(?:wanted\s+)?(?:request\s+)?(?:for\s+)?', '', msg, flags=re.I)
                t_clean = re.sub(r'(?:with\s+)?(?:budget\s+)?(?:of\s+)?(?:rs\.?|for)?\s*\d+.*$', '', t_clean, flags=re.I).strip()
                if len(t_clean) >= 3:
                    ItemRequest.objects.create(user=user, title=t_clean, budget=b_amt, urgency='today', preferred_location='Kumari Hall', description='Posted via AI')
                    Notification.notify_all(f"📢 Wanted: {t_clean[:25]}", f"{user.username} needs this! Rs. {b_amt:.2f}", 'item_wanted', 'fa-bullhorn', '/#wantedBoardSection', exclude_user=user)
                    res.update({'reply': f"Posted request for **{t_clean}** (Budget: Rs. {b_amt:.2f}) to the Wanted Board! Peers have been notified."})
                    return res
            reqs = list(ItemRequest.objects.filter(is_fulfilled=False).select_related('user')[:4])
            lines = ["Recent **Campus Wanted Requests**:"] + [f"• **{r.title}** (Rs. {r.budget:.2f}) • Pickup: *{r.preferred_location}*" for r in reqs] if reqs else ["No open wanted requests right now."]
            res.update({'reply': "\n\n".join(lines)})
            return res

        # 7. Student Blogs
        if any(w in low for w in ['blog', 'article', 'forum', 'study tip', 'guide', 'read blog', 'notes']):
            posts = list(Post.objects.filter(status=True).select_related('category', 'author')[:4])
            lines = ["Popular **Islington Student Blogs & Guides**:"] + [f"• **[{p.title}](/blogs/{p.id}/)** (*{p.category.name}* by *{p.author.username if p.author else 'Student'}*)" for p in posts] if posts else ["No blogs found."]
            res.update({'reply': "\n\n".join(lines), 'action_type': 'blog_list'})
            return res

        # 8. User Orders & Account Tracking
        if any(w in low for w in ['my order', 'track order', 'order status', 'where is my order', 'my purchases']):
            if not user:
                res.update({'reply': "Please **Sign In** to view your orders."})
                return res
            orders = list(Order.objects.filter(user=user).prefetch_related('items')[:3])
            lines = [f"Recent orders for **{user.username}**:"] + [f"• **Order #{o.id}** ({o.order_status.upper()}) — Total: **Rs. {o.total_amount:.2f}** (Pickup: *{o.meetup_location}*)" for o in orders] if orders else ["You have no orders yet."]
            res.update({'reply': "\n\n".join(lines), 'action_type': 'order_status'})
            return res

        # 9. Product Search & AI Reasoning Engine
        qs = Product.objects.filter(status=True, is_approved=True).select_related('category', 'user')
        u_match = re.search(r'(?:under|below|less than|budget of|max(?:imum)?|upto)\s+(?:rs\.?|npr)?\s*(\d+)', low)
        max_p = float(u_match.group(1)) if u_match else None
        if max_p:
            qs = qs.filter(price__lte=max_p)

        cat_match = next((c for c in Category.objects.all() if c.name.lower() in low), None)
        if cat_match:
            qs = qs.filter(category=cat_match)

        clean_q = re.sub(r'\b(find|search|show|me|get|give|looking|for|a|an|the|some|good|best|cheap|cheapest|items|products|under|below|less|than|rs|npr|please|can|you|is|there|any)\b', ' ', low)
        if max_p: clean_q = clean_q.replace(str(int(max_p)), ' ')
        if cat_match: clean_q = clean_q.replace(cat_match.name.lower(), ' ')
        clean_q = re.sub(r'\s+', ' ', clean_q).strip()

        if clean_q and len(clean_q) >= 2:
            f_qs = qs.filter(Q(name__icontains=clean_q) | Q(description__icontains=clean_q))
            qs = f_qs if f_qs.exists() else qs

        if any(w in low for w in ['cheapest', 'lowest price', 'affordable']):
            qs = qs.order_by('price')
        else:
            qs = qs.order_by('-created_at')

        results = list(qs[:6])
        prod_dicts = [AgenticCommerceBot._prod_dict(p) for p in results]

        # Prepare context data for Gemini LLM synthesis
        context_lines = [f"- {p['name']} (Price: {p['formatted_price']}, Category: {p['category']}, Stock: {p['stock']})" for p in prod_dicts]
        context_text = "Available Products in Database:\n" + ("\n".join(context_lines) if context_lines else "No exact matching products in store.")

        # Try Google Gemini AI synthesis first
        ai_reply = AgenticCommerceBot._gemini_generate(msg, context_text)
        if ai_reply:
            first_n = prod_dicts[0]['name'] if prod_dicts else "Items"
            res.update({
                'reply': ai_reply,
                'action_type': 'product_list' if prod_dicts else 'general',
                'products': prod_dicts,
                'quick_replies': [f"Add {first_n[:18]} to cart", 'View Cart', 'Checkout'] if prod_dicts else ['Explore Store', 'Active Auctions', 'My Cart']
            })
            return res

        # Rule-based Fallback
        if not results:
            popular = list(Product.objects.filter(status=True, is_approved=True).select_related('category')[:4])
            res.update({'reply': f"No exact matches found{f' under Rs. {max_p:.2f}' if max_p else ''}. Here are popular items on campus:", 'products': [AgenticCommerceBot._prod_dict(p) for p in popular]})
        else:
            first_n = results[0].name
            res.update({
                'reply': f"Found **{len(results)} item(s)**{f' under Rs. {max_p:.2f}' if max_p else ''}{f' in *{cat_match.name}*' if cat_match else ''}:",
                'action_type': 'product_list',
                'products': prod_dicts,
                'quick_replies': [f"Add {first_n[:18]} to cart", 'View Cart', 'Checkout']
            })

        return res
