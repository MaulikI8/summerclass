import json, threading, urllib.request, urllib.error
from django.conf import settings
from django.contrib.auth.models import User

class EmailMicroservice:
    @classmethod
    def _send(cls, p):
        k = getattr(settings, 'EMAIL_MICROSERVICE_API_KEY', '')
        print("\n" + "="*60 + f"\n[EMAIL MICROSERVICE DISPATCH]\nTo: {p.get('to')}\nSubject: {p.get('subject')}")
        if 'http' in p.get('html', ''):
            import re
            links = re.findall(r'href=[\'"]?(http[^\'" >]+)', p.get('html', ''))
            if links: print(f"Action Link: {links[0]}")
        print("="*60 + "\n")

        if k and not getattr(settings, 'EMAIL_MICROSERVICE_MOCK', False):
            try:
                req = urllib.request.Request(
                    getattr(settings, 'EMAIL_MICROSERVICE_URL', 'https://api.resend.com/emails'),
                    data=json.dumps(p).encode('utf-8'),
                    headers={
                        'Content-Type': 'application/json',
                        'Authorization': f'Bearer {k}',
                        'User-Agent': 'IslingtonMarketplace/1.0'
                    },
                    method='POST'
                )
                with urllib.request.urlopen(req, timeout=10) as r:
                    res_body = r.read().decode('utf-8')
                    print(f"[EMAIL MICROSERVICE LIVE SUCCESS]: {r.status} | {res_body}")
            except urllib.error.HTTPError as he:
                err_data = he.read().decode('utf-8')
                print(f"[EMAIL MICROSERVICE HTTP ERROR {he.code}]: {err_data}")
            except Exception as e:
                print(f"[EMAIL MICROSERVICE ERROR]: {e}")

    @classmethod
    def send_async(cls, to, sub, html):
        if not to: return
        sender = f"{getattr(settings, 'EMAIL_SENDER_NAME', 'Islington Marketplace')} <{getattr(settings, 'EMAIL_SENDER_ADDRESS', 'onboarding@resend.dev')}>"
        p = {'from': sender, 'to': [to] if isinstance(to, str) else to, 'subject': sub, 'html': html}
        threading.Thread(target=cls._send, args=(p,), daemon=True).start()

    @classmethod
    def send_verification_email(cls, u, verify_url):
        if not u.email: return
        name = u.first_name or u.username
        html = f"""<div style="font-family:sans-serif;max-width:540px;margin:0 auto;padding:24px;border:1px solid #e2e8f0;border-radius:12px;text-align:center;">
        <h2 style="color:#2563eb;margin-top:0;">Verify Your Student Registration</h2>
        <p style="color:#334155;">Hi {name}, thanks for joining Islington Marketplace! Click the button below to verify your email and activate your account:</p>
        <p style="margin:26px 0;"><a href="{verify_url}" style="background:#2563eb;color:#ffffff;text-decoration:none;padding:12px 28px;border-radius:30px;font-weight:bold;font-size:15px;display:inline-block;">Verify My Registration</a></p>
        <p style="font-size:12px;color:#64748b;">Direct link: <a href="{verify_url}" style="color:#2563eb;">{verify_url}</a></p>
        <p style="font-size:11px;color:#94a3b8;margin-top:20px;">This link will expire in 24 hours.</p>
        </div>"""
        cls.send_async(u.email, "Verify your Islington Marketplace account", html)

    @classmethod
    def send_product_approved_email(cls, u, p, site_url="https://maulikjoshi.com.np"):
        if not u or not u.email: return
        name = u.first_name or u.username
        prod_url = f"{site_url}/products/{p.id}/"
        html = f"""<div style="font-family:sans-serif;max-width:540px;margin:0 auto;padding:24px;border:1px solid #e2e8f0;border-radius:12px;text-align:center;">
        <span style="background:#10b981;color:#ffffff;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:bold;">✔ Listing Approved</span>
        <h2 style="color:#0f172a;margin-top:16px;">Your Listing is Live!</h2>
        <p style="color:#475569;font-size:15px;">Hi {name}, great news! Your listing <strong>"{p.name}"</strong> has been approved by admin and is now live on the marketplace for <strong>Rs. {p.price:.2f}</strong>.</p>
        <p style="margin:24px 0;"><a href="{prod_url}" style="background:#2563eb;color:#ffffff;text-decoration:none;padding:12px 28px;border-radius:30px;font-weight:bold;font-size:15px;display:inline-block;">View Your Item</a></p>
        <p style="font-size:12px;color:#64748b;">Students can now view, purchase, or bid on your item.</p>
        </div>"""
        cls.send_async(u.email, f'🎉 Your listing "{p.name}" has been approved!', html)

    @classmethod
    def send_product_rejected_email(cls, u, p, reason=""):
        if not u or not u.email: return
        name = u.first_name or u.username
        html = f"""<div style="font-family:sans-serif;max-width:540px;margin:0 auto;padding:24px;border:1px solid #e2e8f0;border-radius:12px;text-align:center;">
        <span style="background:#ef4444;color:#ffffff;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:bold;">⚠️ Listing Moderation Notice</span>
        <h2 style="color:#0f172a;margin-top:16px;">Listing Not Approved</h2>
        <p style="color:#475569;font-size:15px;">Hi {name}, your listing for <strong>"{p.name}"</strong> was reviewed by college admin and could not be approved at this time.</p>
        {f'<p style="background:#fef2f2;border:1px solid #fecaca;padding:12px;border-radius:8px;color:#991b1b;font-size:14px;"><strong>Feedback:</strong> {reason}</p>' if reason else ''}
        <p style="font-size:12px;color:#64748b;">Please verify item details, pricing, and photos, then resubmit from your dashboard.</p>
        </div>"""
        cls.send_async(u.email, f'Listing Update: "{p.name}"', html)

    @classmethod
    def send_product_listed_email(cls, u, p, site_url="https://maulikjoshi.com.np"):
        if not u or not u.email: return
        name = u.first_name or u.username
        prod_url = f"{site_url}/products/{p.id}/"
        html = f"""<div style="font-family:sans-serif;max-width:540px;margin:0 auto;padding:24px;border:1px solid #e2e8f0;border-radius:12px;text-align:center;">
        <h2 style="color:#2563eb;margin-top:0;">Listing Published!</h2>
        <p style="color:#334155;">Hi {name}, your item <strong>{p.name}</strong> is live for <strong>Rs. {p.price:.2f}</strong>.</p>
        <p style="margin:24px 0;"><a href="{prod_url}" style="background:#2563eb;color:#ffffff;text-decoration:none;padding:12px 28px;border-radius:30px;font-weight:bold;font-size:15px;display:inline-block;">View Item</a></p>
        </div>"""
        cls.send_async(u.email, f'Listing Live: "{p.name}"', html)

    @classmethod
    def send_new_auction_broadcast(cls, auction, auction_url):
        # Email all registered active students via Resend
        emails = list(User.objects.filter(is_active=True).exclude(email='').values_list('email', flat=True))
        if not emails: return
        html = f"""<div style="font-family:sans-serif;max-width:540px;margin:0 auto;padding:24px;border:1px solid #e2e8f0;border-radius:12px;text-align:center;">
        <span style="background:#ef4444;color:#ffffff;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:bold;text-transform:uppercase;">🔥 24-Hour Live Auction</span>
        <h2 style="color:#0f172a;margin-top:16px;">{auction.title}</h2>
        <p style="color:#475569;font-size:15px;">A new 24-hour peer auction has just begun! Starting price is <strong>Rs. {auction.starting_bid:.2f}</strong>.</p>
        <p style="margin:24px 0;"><a href="{auction_url}" style="background:#2563eb;color:#ffffff;text-decoration:none;padding:12px 28px;border-radius:30px;font-weight:bold;font-size:15px;display:inline-block;">Place a Bid Now</a></p>
        <p style="font-size:12px;color:#64748b;">Auction ends in 24 hours or whenever the seller accepts the highest bid.</p>
        </div>"""
        cls.send_async(emails, f"🔥 New 24-Hour Live Auction: {auction.title}", html)

    @classmethod
    def send_outbid_notification(cls, outbid_user, auction, new_bid_amount, auction_url):
        if not outbid_user or not outbid_user.email: return
        name = outbid_user.first_name or outbid_user.username
        html = f"""<div style="font-family:sans-serif;max-width:540px;margin:0 auto;padding:24px;border:1px solid #e2e8f0;border-radius:12px;text-align:center;">
        <span style="background:#f59e0b;color:#ffffff;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:bold;">⚠️ Outbid Alert</span>
        <h2 style="color:#0f172a;margin-top:16px;">You've been outbid on {auction.title}!</h2>
        <p style="color:#475569;font-size:15px;">Hi {name}, another student just placed a higher bid of <strong style="color:#2563eb;">Rs. {new_bid_amount:.2f}</strong>.</p>
        <p style="margin:24px 0;"><a href="{auction_url}" style="background:#ef4444;color:#ffffff;text-decoration:none;padding:12px 28px;border-radius:30px;font-weight:bold;font-size:15px;display:inline-block;">Raise Your Bid</a></p>
        <p style="font-size:12px;color:#64748b;">Bid again before the 24-hour timer expires!</p>
        </div>"""
        cls.send_async(outbid_user.email, f"⚠️ You've been outbid on {auction.title}!", html)

    @classmethod
    def send_auction_won_notification(cls, winner, seller, auction, site_url="https://maulikjoshi.com.np"):
        if winner and winner.email:
            name = winner.first_name or winner.username
            order_url = f"{site_url}/profile/?tab=orders"
            html = f"""<div style="font-family:sans-serif;max-width:540px;margin:0 auto;padding:24px;border:1px solid #e2e8f0;border-radius:12px;text-align:center;">
            <span style="background:#10b981;color:#ffffff;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:bold;">🎉 Auction Won</span>
            <h2 style="color:#0f172a;margin-top:16px;">Congratulations {name}!</h2>
            <p style="color:#475569;font-size:15px;">You won the auction for <strong>{auction.title}</strong> with the winning bid of <strong>Rs. {auction.current_bid:.2f}</strong>!</p>
            <p style="margin:24px 0;"><a href="{order_url}" style="background:#10b981;color:#ffffff;text-decoration:none;padding:12px 28px;border-radius:30px;font-weight:bold;font-size:15px;display:inline-block;">View in My Orders</a></p>
            <p style="font-size:12px;color:#64748b;">Arrange safe collection directly with the seller {seller.username if seller else 'peer'}.</p>
            </div>"""
            cls.send_async(winner.email, f"🎉 You Won the Auction for {auction.title}!", html)

    @classmethod
    def send_order_confirmation_email(cls, order, site_url="https://maulikjoshi.com.np"):
        if not order.buyer_email: return
        html = f"""<div style="font-family:sans-serif;max-width:540px;margin:0 auto;padding:24px;border:1px solid #e2e8f0;border-radius:12px;text-align:center;">
        <span style="background:#2563eb;color:#ffffff;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:bold;">📦 Order Confirmed</span>
        <h2 style="color:#0f172a;margin-top:16px;">Order #{order.id} Placed Successfully!</h2>
        <p style="color:#475569;font-size:15px;">Thank you {order.buyer_name}! Your order total is <strong>Rs. {order.total_amount:.2f}</strong>.</p>
        <p style="background:#f8fafc;padding:12px;border-radius:8px;text-align:left;font-size:14px;color:#334155;">
        <strong>Pickup Location:</strong> {order.meetup_location}<br>
        <strong>Preferred Time:</strong> {order.meetup_time}<br>
        <strong>Payment Status:</strong> {order.payment_status}
        </p>
        <p style="margin:24px 0;"><a href="{site_url}/profile/?tab=orders" style="background:#2563eb;color:#ffffff;text-decoration:none;padding:12px 28px;border-radius:30px;font-weight:bold;font-size:15px;display:inline-block;">View My Order</a></p>
        </div>"""
        cls.send_async(order.buyer_email, f"Order #{order.id} Confirmation - Islington Marketplace", html)
