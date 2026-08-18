import re
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
from products.models import Product, Category, Auction, ItemRequest, Order
from blog.models import Post, Category as BlogCategory
from sitesetting.models import Notification, SiteSetting
from cart.models import Cart, CartItem
from cart.views import _get_or_create_cart

class AgenticCommerceBot:
    @staticmethod
    def process_query(message: str, request) -> dict:
        msg = message.strip()
        msg_lower = msg.lower()
        cart = _get_or_create_cart(request)
        user = request.user if request.user.is_authenticated else None

        # -------------------------------------------------------------
        # 1. INTENT: Direct Add to Cart Action
        # -------------------------------------------------------------
        if (msg_lower.startswith('add ') or msg_lower.startswith('buy ')) and not any(w in msg_lower for w in ['how to buy', 'how to add']):
            target_name = re.sub(r'^(?:add|buy)\s+(?:the\s+)?', '', msg_lower)
            target_name = re.sub(r'\s+(?:to\s+(?:my\s+)?cart|in\s+(?:my\s+)?cart|now)$', '', target_name).strip()
            if target_name and len(target_name) > 1:
                return AgenticCommerceBot._handle_add_to_cart(target_name, cart, request)
        elif 'to cart' in msg_lower or 'in my cart' in msg_lower:
            add_match = re.search(r'(?:add|put|buy)\s+(?:the\s+)?(.+?)\s+(?:to\s+(?:my\s+)?cart|in\s+(?:my\s+)?cart)', msg_lower)
            if add_match:
                target_name = add_match.group(1).strip()
                if target_name:
                    return AgenticCommerceBot._handle_add_to_cart(target_name, cart, request)

        # -------------------------------------------------------------
        # 2. INTENT: View / Show Cart Summary
        # -------------------------------------------------------------
        if re.search(r'\b(?:show|view|check|open|my|see)\s*(?:my\s+)?(?:cart|basket|bag|summary)\b', msg_lower) or msg_lower in ['cart', 'my cart', 'view cart', 'show cart']:
            return AgenticCommerceBot._handle_view_cart(cart)

        # -------------------------------------------------------------
        # 3. INTENT: Clear / Empty Cart
        # -------------------------------------------------------------
        if any(w in msg_lower for w in ['clear cart', 'empty cart', 'clear my cart', 'delete cart', 'empty my cart']):
            cart.items.all().delete()
            return {
                'reply': "Your shopping cart has been completely cleared.",
                'action_type': 'cart_cleared',
                'products': [],
                'cart_data': {'count': 0, 'total': 0.0},
                'quick_replies': ['Explore Store', 'Active Auctions', 'Show Textbooks']
            }

        # -------------------------------------------------------------
        # 4. INTENT: Checkout Direct Action
        # -------------------------------------------------------------
        if any(w in msg_lower for w in ['checkout', 'proceed to pay', 'buy all', 'place order', 'go to checkout']):
            cart_count = cart.total_items_count
            if cart_count == 0:
                return {
                    'reply': "Your cart is currently empty! Ask me to find products for you first.",
                    'action_type': 'general',
                    'products': [],
                    'cart_data': {'count': 0, 'total': 0.0},
                    'quick_replies': ['Show Popular Items', 'Active Auctions', 'Search Textbooks']
                }
            return {
                'reply': f"You have **{cart_count} item(s)** totaling **Rs. {cart.total_price:.2f}** ready for checkout with Islington Campus Pickup.",
                'action_type': 'checkout_redirect',
                'redirect_url': '/checkout/',
                'products': [],
                'cart_data': {'count': cart_count, 'total': cart.total_price},
                'quick_replies': ['View Cart', 'Continue Shopping']
            }

        # -------------------------------------------------------------
        # 5. INTENT: Remove single item from cart
        # -------------------------------------------------------------
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

        # -------------------------------------------------------------
        # 6. INTENT: 24h Live Flash Auctions
        # -------------------------------------------------------------
        if any(w in msg_lower for w in ['auction', 'bid', 'bidding', 'flash auction', 'ending soon']):
            return AgenticCommerceBot._handle_auctions()

        # -------------------------------------------------------------
        # 7. INTENT: Campus Wanted Board (Reverse Marketplace)
        # -------------------------------------------------------------
        if any(w in msg_lower for w in ['wanted', 'request', 'looking for', 'need book', 'need kit', 'item request']):
            # Check if user wants to post a wanted request
            post_match = re.search(r'(?:post|create|add)?\s*(?:a\s+)?(?:wanted\s+)?request(?:\s+for)?\s+(.+)', msg_lower)
            if post_match and ('need' in msg_lower or 'budget' in msg_lower or 'post' in msg_lower):
                return AgenticCommerceBot._handle_post_wanted_request(msg, user)
            return AgenticCommerceBot._handle_view_wanted_requests()

        # -------------------------------------------------------------
        # 8. INTENT: Student Blogs & Community Discussions
        # -------------------------------------------------------------
        if any(w in msg_lower for w in ['blog', 'article', 'forum', 'study tip', 'guide', 'read blog', 'notes']):
            return AgenticCommerceBot._handle_blogs(msg_lower)

        # -------------------------------------------------------------
        # 9. INTENT: User Orders & Tracking (Account context)
        # -------------------------------------------------------------
        if any(w in msg_lower for w in ['my order', 'track order', 'order status', 'where is my order', 'my purchases']):
            return AgenticCommerceBot._handle_user_orders(user, msg_lower)

        # -------------------------------------------------------------
        # 10. INTENT: User My Listings & Selling Status
        # -------------------------------------------------------------
        if any(w in msg_lower for w in ['my listing', 'my items', 'what am i selling', 'my posted products', 'my store']):
            return AgenticCommerceBot._handle_user_listings(user)

        # -------------------------------------------------------------
        # 11. INTENT: Notifications Hub
        # -------------------------------------------------------------
        if any(w in msg_lower for w in ['notification', 'unread', 'alert', 'inbox']):
            return AgenticCommerceBot._handle_user_notifications(user)

        # -------------------------------------------------------------
        # 12. INTENT: Campus Pickup & Logistics Guide
        # -------------------------------------------------------------
        if any(w in msg_lower for w in ['pickup', 'location', 'where', 'block', 'kumari hall', 'skill block', 'nepal block', 'brit house', 'timing', 'hours', 'contact', 'phone', 'email']):
            return AgenticCommerceBot._handle_campus_info()

        # -------------------------------------------------------------
        # 13. INTENT: Product Search, Catalog Filter & Discovery (Default)
        # -------------------------------------------------------------
        return AgenticCommerceBot._handle_product_search(msg, msg_lower, cart)

    # =========================================================================
    # HANDLER: Cart Operations
    # =========================================================================
    @staticmethod
    def _handle_view_cart(cart) -> dict:
        items = cart.items.filter(is_active=True).select_related('product')
        if not items.exists():
            return {
                'reply': "Your cart is currently empty. What would you like to shop for today?",
                'action_type': 'cart_summary',
                'products': [],
                'cart_data': {'count': 0, 'total': 0.0},
                'quick_replies': ['Find Electronics', 'Active Auctions', 'Show Textbooks']
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
            'quick_replies': ['Show All Products', 'Active Auctions', 'Find Textbooks']
        }

    # =========================================================================
    # HANDLER: 24h Live Flash Auctions
    # =========================================================================
    @staticmethod
    def _handle_auctions() -> dict:
        auctions = list(Auction.objects.filter(is_active=True, end_time__gt=timezone.now(), product__is_approved=True).select_related('product', 'highest_bidder', 'product__user').order_by('end_time')[:4])
        if not auctions:
            return {
                'reply': "There are currently no active live auctions. You can browse regular store listings or post your own 24h auction from your Profile!",
                'action_type': 'general',
                'products': [],
                'quick_replies': ['Explore Store', 'Post New Listing', 'Wanted Board']
            }
        
        lines = ["Here are the **24-Hour Live Auctions** active right now:"]
        products = []
        for a in auctions:
            remaining = a.end_time - timezone.now()
            hrs, mins = int(remaining.total_seconds() // 3600), int((remaining.total_seconds() % 3600) // 60)
            bid_info = f"Current Bid: **Rs. {a.current_bid:.2f}** ({a.bids_count} bids) • Ends in: **{hrs}h {mins}m**"
            lines.append(f"• **{a.title}**\n  {bid_info}")
            if a.product:
                products.append(AgenticCommerceBot._serialize_product(a.product))

        return {
            'reply': "\n\n".join(lines),
            'action_type': 'auction_list',
            'products': products,
            'quick_replies': ['Go to Live Bidding', 'Explore Store', 'Show My Cart']
        }

    # =========================================================================
    # HANDLER: Campus Wanted Board
    # =========================================================================
    @staticmethod
    def _handle_view_wanted_requests() -> dict:
        requests = list(ItemRequest.objects.filter(is_fulfilled=False).select_related('user', 'category').order_by('-created_at')[:4])
        if not requests:
            return {
                'reply': "There are no open wanted requests right now. Looking for something specific? Ask me to post a request for you!",
                'action_type': 'general',
                'products': [],
                'quick_replies': ['Post Item Request', 'Explore Store']
            }
        
        lines = ["Here are recent **Campus Wanted Requests** from fellow students:"]
        for r in requests:
            lines.append(f"• **{r.title}** (Budget: Rs. {r.budget:.2f})\n  Pickup: *{r.preferred_location}* • Urgency: *{r.get_urgency_display()}*")
        
        return {
            'reply': "\n\n".join(lines) + "\n\n*Have any of these? Visit the Wanted Board on the Home page to click 'I Have This!' and connect.*",
            'action_type': 'wanted_list',
            'products': [],
            'quick_replies': ['View Wanted Board', 'Explore Store', 'My Cart']
        }

    @staticmethod
    def _handle_post_wanted_request(raw_msg: str, user) -> dict:
        if not user:
            return {
                'reply': "Please **Sign In** to post a request on the Campus Wanted Board so peers can notify you when they have your item.",
                'action_type': 'general',
                'products': [],
                'quick_replies': ['Student Sign In', 'Explore Store']
            }
        
        # Extract title and optional budget
        budget_match = re.search(r'(?:budget|rs\.?|for)\s*(\d+)', raw_msg, re.IGNORECASE)
        budget = float(budget_match.group(1)) if budget_match else 0.0
        
        clean_title = re.sub(r'^(?:post|create|add)?\s*(?:a\s+)?(?:wanted\s+)?(?:request\s+)?(?:for\s+)?', '', raw_msg, flags=re.IGNORECASE)
        clean_title = re.sub(r'(?:with\s+)?(?:budget\s+)?(?:of\s+)?(?:rs\.?|for)?\s*\d+.*$', '', clean_title, flags=re.IGNORECASE).strip()
        
        if len(clean_title) >= 3:
            req = ItemRequest.objects.create(
                user=user,
                title=clean_title,
                budget=budget,
                urgency='today',
                preferred_location='Kumari Hall',
                description='Posted via AI Assistant'
            )
            Notification.notify_all(f"📢 Wanted: {clean_title[:25]}", f"{user.username} is looking for this! Budget: Rs. {budget:.2f}", 'item_wanted', 'fa-bullhorn', '/#wantedBoardSection', exclude_user=user)
            return {
                'reply': f"Posted your request for **{clean_title}** (Budget: Rs. {budget:.2f}) on the **Campus Wanted Board**! Peers will be notified immediately.",
                'action_type': 'general',
                'products': [],
                'quick_replies': ['View Wanted Board', 'Explore Store', 'My Cart']
            }

        return {
            'reply': "To post an item request, tell me what you need and your budget (e.g. *'Post request for Arduino Kit budget 500'*).",
            'action_type': 'general',
            'products': [],
            'quick_replies': ['Show Wanted Board', 'Browse Store']
        }

    # =========================================================================
    # HANDLER: Student Blogs & Articles
    # =========================================================================
    @staticmethod
    def _handle_blogs(msg_lower: str) -> dict:
        posts = Post.objects.filter(status=True).select_related('category', 'author').order_by('-created_at')
        
        # Check for category match
        for cat in BlogCategory.objects.all():
            if cat.name.lower() in msg_lower:
                posts = posts.filter(category=cat)
                break

        results = list(posts[:4])
        if not results:
            return {
                'reply': "No blog posts found matching that topic. Check out our latest articles in the Blogs section!",
                'action_type': 'general',
                'products': [],
                'quick_replies': ['Go to Blogs', 'Explore Store']
            }
        
        lines = ["Here are popular **Islington Student Blogs & Guides**:"]
        for p in results:
            author_name = p.author.username if p.author else "Islington Student"
            lines.append(f"• **[{p.title}](/blogs/{p.id}/)** (*{p.category.name}* by *{author_name}*)\n  {p.content[:90]}...")
        
        return {
            'reply': "\n\n".join(lines),
            'action_type': 'blog_list',
            'products': [],
            'quick_replies': ['View All Blogs', 'Explore Store', 'My Cart']
        }

    # =========================================================================
    # HANDLER: User Orders & Tracking
    # =========================================================================
    @staticmethod
    def _handle_user_orders(user, msg_lower: str) -> dict:
        if not user:
            return {
                'reply': "Please **Sign In** to view and track your campus orders.",
                'action_type': 'general',
                'products': [],
                'quick_replies': ['Student Sign In', 'Explore Store']
            }
        
        orders = list(Order.objects.filter(user=user).prefetch_related('items').order_by('-created_at')[:3])
        if not orders:
            return {
                'reply': "You haven't placed any orders yet. Would you like me to help you find some products?",
                'action_type': 'general',
                'products': [],
                'quick_replies': ['Explore Store', 'Find Electronics', 'Active Auctions']
            }
        
        lines = [f"Here are your recent orders for **{user.username}**:"]
        for o in orders:
            items_str = ", ".join([f"{i.quantity}x {i.product_name}" for i in o.items.all()]) or "Items"
            lines.append(f"• **Order #{o.id}** — Status: **{o.order_status.upper()}**\n  Items: *{items_str}*\n  Total: **Rs. {o.total_amount:.2f}** • Meetup: *{o.meetup_location}* ({o.meetup_time})")
        
        return {
            'reply': "\n\n".join(lines),
            'action_type': 'order_status',
            'products': [],
            'quick_replies': ['Go to My Profile', 'Explore Store', 'My Cart']
        }

    # =========================================================================
    # HANDLER: User Listings / Selling
    # =========================================================================
    @staticmethod
    def _handle_user_listings(user) -> dict:
        if not user:
            return {
                'reply': "Please **Sign In** to check your active seller listings.",
                'action_type': 'general',
                'products': [],
                'quick_replies': ['Student Sign In', 'Explore Store']
            }
        
        listings = list(Product.objects.filter(user=user).order_by('-created_at')[:4])
        if not listings:
            return {
                'reply': "You haven't posted any listings yet. You can post textbooks, electronics, or college gear from your Profile!",
                'action_type': 'general',
                'products': [],
                'quick_replies': ['Post New Listing', 'Explore Store']
            }
        
        lines = [f"You have **{len(listings)} active listing(s)**:"]
        for p in listings:
            status_tag = "Approved" if p.is_approved else "Pending Review"
            lines.append(f"• **{p.name}** — Rs. {p.price:.2f} (Stock: {p.stock}, Status: *{status_tag}*)")
        
        return {
            'reply': "\n\n".join(lines),
            'action_type': 'user_listings',
            'products': [AgenticCommerceBot._serialize_product(p) for p in listings],
            'quick_replies': ['Post New Listing', 'My Profile', 'Explore Store']
        }

    # =========================================================================
    # HANDLER: User Notifications
    # =========================================================================
    @staticmethod
    def _handle_user_notifications(user) -> dict:
        if not user:
            return {
                'reply': "Please **Sign In** to check your notifications.",
                'action_type': 'general',
                'products': [],
                'quick_replies': ['Student Sign In', 'Explore Store']
            }
        
        notifs = list(Notification.objects.filter(recipient=user, is_read=False).order_by('-created_at')[:4])
        if not notifs:
            return {
                'reply': "You have **no unread notifications**. You're all caught up!",
                'action_type': 'general',
                'products': [],
                'quick_replies': ['Explore Store', 'Active Auctions', 'My Cart']
            }
        
        lines = [f"You have **{len(notifs)} unread notification(s)**:"]
        for n in notifs:
            lines.append(f"• **{n.title}**\n  {n.message}")
        
        return {
            'reply': "\n\n".join(lines),
            'action_type': 'notifications',
            'products': [],
            'quick_replies': ['My Profile', 'Explore Store', 'My Cart']
        }

    # =========================================================================
    # HANDLER: Campus Logistics & Info
    # =========================================================================
    @staticmethod
    def _handle_campus_info() -> dict:
        info = (
            "📍 **Islington College Campus Pickup Locations:**\n\n"
            "• **Kumari Hall** (Primary Central Meetup Spot)\n"
            "• **Skill Block** (3rd Floor Lab Lobby)\n"
            "• **Nepal Block** (Ground Floor Common Area)\n"
            "• **Alumini Block** (Front Reception)\n"
            "• **Brit House** & **Main/Himal Block**\n\n"
            "⏰ **Standard Handover Hours:** 10:00 AM – 4:00 PM (Monday to Friday)\n"
            "💳 **Payment:** Campus Cash on Delivery (COD) or eSewa Sandbox online payment.\n"
            "📧 **Contact:** info@islingtonmarket.np | +977-1-4412345"
        )
        return {
            'reply': info,
            'action_type': 'campus_info',
            'products': [],
            'quick_replies': ['Explore Store', 'Active Auctions', 'View My Cart']
        }

    # =========================================================================
    # HANDLER: Product Search & Recommendation
    # =========================================================================
    @staticmethod
    def _handle_product_search(raw_msg: str, msg_lower: str, cart) -> dict:
        qs = Product.objects.filter(status=True, is_approved=True).select_related('category', 'user')

        # 1. Budget extraction
        max_price, min_price = None, None
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
            all_recent = list(Product.objects.filter(status=True, is_approved=True).select_related('category')[:4])
            reply = "I couldn't find active listings matching your exact criteria"
            if max_price:
                reply += f" under Rs. {max_price:.2f}"
            reply += ". Here are popular items currently available in the campus store:"
            return {
                'reply': reply,
                'action_type': 'product_list',
                'products': [AgenticCommerceBot._serialize_product(p) for p in all_recent],
                'cart_data': {'count': cart.total_items_count, 'total': cart.total_price},
                'quick_replies': ['Show All Products', 'Active Auctions', 'View Cart']
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
