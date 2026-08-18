import re
from django.db.models import Q
from products.models import Product, Category
from cart.models import Cart, CartItem
from cart.views import _get_or_create_cart

class AgenticCommerceBot:
    @staticmethod
    def process_query(message: str, request) -> dict:
        msg = message.strip()
        msg_lower = msg.lower()
        cart = _get_or_create_cart(request)

        # 1. Intent: Direct Add to Cart Action by name or command
        add_match = re.search(r'(?:add|put|buy)\s+(?:the\s+)?(.+?)(?:\s+(?:to\s+(?:my\s+)?cart|in\s+(?:my\s+)?cart|now))?$', msg_lower)
        if (msg_lower.startswith('add ') or msg_lower.startswith('buy ')) and not any(w in msg_lower for w in ['how to buy', 'how to add']):
            target_name = re.sub(r'^(?:add|buy)\s+(?:the\s+)?', '', msg_lower)
            target_name = re.sub(r'\s+(?:to\s+(?:my\s+)?cart|in\s+(?:my\s+)?cart|now)$', '', target_name).strip()
            if target_name and len(target_name) > 1:
                return AgenticCommerceBot._handle_add_to_cart(target_name, cart, request)
        elif 'to cart' in msg_lower or 'in my cart' in msg_lower:
            add_match_inline = re.search(r'(?:add|put|buy)\s+(?:the\s+)?(.+?)\s+(?:to\s+(?:my\s+)?cart|in\s+(?:my\s+)?cart)', msg_lower)
            if add_match_inline:
                target_name = add_match_inline.group(1).strip()
                if target_name:
                    return AgenticCommerceBot._handle_add_to_cart(target_name, cart, request)

        # 2. Intent: View / Show Cart Summary
        if re.search(r'\b(?:show|view|check|open|my|see)\s*(?:my\s+)?(?:cart|basket|bag|summary)\b', msg_lower) or msg_lower in ['cart', 'my cart', 'view cart', 'show cart']:
            return AgenticCommerceBot._handle_view_cart(cart)

        # 3. Intent: Clear / Empty Cart
        if any(w in msg_lower for w in ['clear cart', 'empty cart', 'clear my cart', 'delete cart', 'empty my cart']):
            cart.items.all().delete()
            return {
                'reply': "Your shopping cart has been completely cleared.",
                'action_type': 'cart_cleared',
                'products': [],
                'cart_data': {'count': 0, 'total': 0.0},
                'quick_replies': ['Explore Store', 'Find Electronics under Rs. 1000', 'Show Textbooks']
            }

        # 4. Intent: Checkout Direct Action
        if any(w in msg_lower for w in ['checkout', 'proceed to pay', 'buy all', 'place order', 'go to checkout']):
            cart_count = cart.total_items_count
            if cart_count == 0:
                return {
                    'reply': "Your cart is currently empty! Ask me to find products for you first.",
                    'action_type': 'general',
                    'products': [],
                    'cart_data': {'count': 0, 'total': 0.0},
                    'quick_replies': ['Show Popular Items', 'Find Electronics', 'Search Textbooks']
                }
            return {
                'reply': f"You have **{cart_count} item(s)** totaling **Rs. {cart.total_price:.2f}** ready for checkout with Islington Campus Pickup.",
                'action_type': 'checkout_redirect',
                'redirect_url': '/checkout/',
                'products': [],
                'cart_data': {'count': cart_count, 'total': cart.total_price},
                'quick_replies': ['View Cart', 'Continue Shopping']
            }

        # 5. Intent: Remove single item from cart
        rem_match = re.search(r'(?:remove|delete|drop)\s+(?:the\s+)?(.+?)\s+(?:from\s+(?:my\s+)?cart|out\s+of\s+cart)', msg_lower)
        if rem_match:
            item_name = rem_match.group(1).strip()
            item = cart.items.filter(product__name__icontains=item_name).first()
            if item:
                prod_name = item.product.name
                item.delete()
                return {
                    'reply': f"Removed **{prod_name}** from your cart.",
                    'action_type': 'cart_updated',
                    'products': [],
                    'cart_data': {'count': cart.total_items_count, 'total': cart.total_price},
                    'quick_replies': ['View Cart', 'Checkout Now', 'Find More Items']
                }
            return {
                'reply': f"I couldn't find '{item_name}' in your active cart.",
                'action_type': 'general',
                'products': [],
                'cart_data': {'count': cart.total_items_count, 'total': cart.total_price},
                'quick_replies': ['Show My Cart', 'Browse Store']
            }

        # 6. Intent: Search, Filter, and Recommend Products
        return AgenticCommerceBot._handle_product_search(msg, msg_lower, cart)

    @staticmethod
    def _handle_view_cart(cart) -> dict:
        items = cart.items.filter(is_active=True).select_related('product')
        if not items.exists():
            return {
                'reply': "Your cart is currently empty. What would you like to shop for today?",
                'action_type': 'cart_summary',
                'products': [],
                'cart_data': {'count': 0, 'total': 0.0},
                'quick_replies': ['Find Electronics', 'Search Textbooks', 'Show Popular Items']
            }
        
        breakdown = []
        for it in items:
            breakdown.append(f"• **{it.quantity}x {it.product.name}** — Rs. {it.sub_total:.2f}")
        
        reply_text = f"Here is your active cart (**{cart.total_items_count} items**):\n\n" + "\n".join(breakdown) + f"\n\n**Total: Rs. {cart.total_price:.2f}**"
        return {
            'reply': reply_text,
            'action_type': 'cart_summary',
            'products': [AgenticCommerceBot._serialize_product(it.product) for it in items],
            'cart_data': {'count': cart.total_items_count, 'total': cart.total_price},
            'quick_replies': ['Proceed to Checkout', 'Clear Cart', 'Continue Shopping']
        }

    @staticmethod
    def _handle_add_to_cart(target_name: str, cart, request) -> dict:
        qs = Product.objects.filter(status=True, is_approved=True).select_related('category', 'user')
        prod = qs.filter(name__iexact=target_name).first() or qs.filter(name__icontains=target_name).first()
        
        if not prod:
            # Fallback fuzzy matching in description or category
            prod = qs.filter(Q(description__icontains=target_name) | Q(category__name__icontains=target_name)).first()

        if prod:
            if request.user.is_authenticated and prod.user == request.user:
                return {
                    'reply': f"You cannot add **{prod.name}** to your cart because you listed it yourself!",
                    'action_type': 'general',
                    'products': [AgenticCommerceBot._serialize_product(prod)],
                    'cart_data': {'count': cart.total_items_count, 'total': cart.total_price},
                    'quick_replies': ['Find Other Items', 'View Cart']
                }

            if prod.stock <= 0:
                return {
                    'reply': f"Sorry, **{prod.name}** is currently out of stock.",
                    'action_type': 'general',
                    'products': [AgenticCommerceBot._serialize_product(prod)],
                    'cart_data': {'count': cart.total_items_count, 'total': cart.total_price},
                    'quick_replies': ['Find Similar Items', 'Explore Store']
                }

            item, created = CartItem.objects.get_or_create(cart=cart, product=prod)
            if not created:
                item.quantity = min(item.quantity + 1, prod.stock or 1)
                item.save()

            return {
                'reply': f"Added **{prod.name}** (Rs. {prod.price:.2f}) directly to your cart!",
                'action_type': 'cart_updated',
                'products': [AgenticCommerceBot._serialize_product(prod)],
                'cart_data': {'count': cart.total_items_count, 'total': cart.total_price},
                'quick_replies': ['Proceed to Checkout', 'View Cart', 'Find More Items']
            }

        return {
            'reply': f"I couldn't find a product matching '{target_name}'. Try browsing categories or searching with a different keyword.",
            'action_type': 'general',
            'products': [],
            'cart_data': {'count': cart.total_items_count, 'total': cart.total_price},
            'quick_replies': ['Show All Products', 'Find Electronics', 'Find Textbooks']
        }

    @staticmethod
    def _handle_product_search(raw_msg: str, msg_lower: str, cart) -> dict:
        qs = Product.objects.filter(status=True, is_approved=True).select_related('category', 'user')

        # 1. Budget extraction (under / below / less than / budget of / max Rs. X)
        max_price = None
        min_price = None

        range_match = re.search(r'(?:between|from)\s+(?:rs\.?|npr)?\s*(\d+)\s+(?:and|to)\s+(?:rs\.?|npr)?\s*(\d+)', msg_lower)
        if range_match:
            min_price, max_price = float(range_match.group(1)), float(range_match.group(2))
        else:
            under_match = re.search(r'(?:under|below|less than|max(?:imum)?|budget of|upto|up to)\s+(?:rs\.?|npr)?\s*(\d+)', msg_lower)
            if under_match:
                max_price = float(under_match.group(1))

        if max_price is not None:
            qs = qs.filter(price__lte=max_price)
        if min_price is not None:
            qs = qs.filter(price__gte=min_price)

        # 2. Category matching
        categories = list(Category.objects.all())
        matched_category = None
        for cat in categories:
            if cat.name.lower() in msg_lower:
                matched_category = cat
                qs = qs.filter(category=cat)
                break

        # 3. Clean search keywords
        clean_query = msg_lower
        remove_words = ['find', 'search', 'show', 'me', 'get', 'give', 'looking', 'for', 'a', 'an', 'the', 'some', 'good', 'best', 'cheap', 'cheapest', 'items', 'products', 'under', 'below', 'less', 'than', 'rs', 'npr', 'please', 'can', 'you', 'is', 'there', 'any']
        for rw in remove_words:
            clean_query = re.sub(rf'\b{rw}\b', ' ', clean_query)
        if max_price:
            clean_query = clean_query.replace(str(int(max_price)), ' ')
        if min_price:
            clean_query = clean_query.replace(str(int(min_price)), ' ')
        if matched_category:
            clean_query = clean_query.replace(matched_category.name.lower(), ' ')

        clean_query = re.sub(r'\s+', ' ', clean_query).strip()

        if clean_query and len(clean_query) >= 2:
            query_filter = Q(name__icontains=clean_query) | Q(description__icontains=clean_query)
            filtered_qs = qs.filter(query_filter)
            if filtered_qs.exists():
                qs = filtered_qs
            else:
                # Try word by word
                words = clean_query.split()
                if len(words) > 1:
                    word_filter = Q()
                    for w in words:
                        if len(w) > 2:
                            word_filter |= Q(name__icontains=w) | Q(description__icontains=w)
                    if word_filter:
                        fallback_qs = qs.filter(word_filter)
                        if fallback_qs.exists():
                            qs = fallback_qs

        # Sort preference
        if any(w in msg_lower for w in ['cheapest', 'lowest price', 'affordable']):
            qs = qs.order_by('price')
        elif any(w in msg_lower for w in ['expensive', 'highest price', 'premium']):
            qs = qs.order_by('-price')
        else:
            qs = qs.order_by('-created_at')

        results = list(qs[:6])

        if not results:
            # Smart alternative recommendation if no direct match
            all_recent = list(Product.objects.filter(status=True, is_approved=True).select_related('category')[:4])
            reply = f"I couldn't find active listings matching your exact criteria"
            if max_price:
                reply += f" under Rs. {max_price:.2f}"
            reply += ". Here are popular items currently available in the campus store:"
            return {
                'reply': reply,
                'action_type': 'product_list',
                'products': [AgenticCommerceBot._serialize_product(p) for p in all_recent],
                'cart_data': {'count': cart.total_items_count, 'total': cart.total_price},
                'quick_replies': ['Show All Products', 'Find Electronics', 'View Cart']
            }

        count = len(results)
        reply = f"Found **{count} item(s)** matching your request"
        if max_price:
            reply += f" under Rs. {max_price:.2f}"
        if matched_category:
            reply += f" in *{matched_category.name}*"
        reply += ":"

        serialized = [AgenticCommerceBot._serialize_product(p) for p in results]
        first_name = results[0].name
        return {
            'reply': reply,
            'action_type': 'product_list',
            'products': serialized,
            'cart_data': {'count': cart.total_items_count, 'total': cart.total_price},
            'quick_replies': [f"Add {first_name[:20]} to cart", 'View Cart', 'Checkout']
        }

    @staticmethod
    def _serialize_product(p: Product) -> dict:
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
