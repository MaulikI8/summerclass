import json, threading, requests
from django.conf import settings
from django.contrib.auth.models import User

class EmailMicroservice:
    @classmethod
    def _send(cls, p):
        k = getattr(settings, 'EMAIL_MICROSERVICE_API_KEY', '')
        smtp_user = getattr(settings, 'EMAIL_HOST_USER', '')
        smtp_pass = getattr(settings, 'EMAIL_HOST_PASSWORD', '')
        to_addr = p.get('to')
        subject = p.get('subject')
        print(f"\n[EMAIL DISPATCH] To: {to_addr} | Subject: {subject}")

        # Method 1: If Gmail / SMTP credentials are configured, send directly via SMTP
        if smtp_user and smtp_pass and not getattr(settings, 'EMAIL_MICROSERVICE_MOCK', False):
            try:
                from django.core.mail import EmailMultiAlternatives
                recipients = to_addr if isinstance(to_addr, list) else [to_addr]
                msg = EmailMultiAlternatives(
                    subject=subject,
                    body="Please view this email in an HTML-compatible client.",
                    from_email=f"{getattr(settings, 'EMAIL_SENDER_NAME', 'Islington Marketplace')} <{smtp_user}>",
                    to=recipients
                )
                if p.get('html'):
                    msg.attach_alternative(p.get('html'), 'text/html')
                msg.send(fail_silently=False)
                print(f"[EMAIL SUCCESS (SMTP)]: Delivered to {recipients}")
                return
            except Exception as e:
                print(f"[EMAIL SMTP ERROR]: {e}")

        # Method 2: Resend API Dispatch
        if k and not getattr(settings, 'EMAIL_MICROSERVICE_MOCK', False):
            try:
                url = getattr(settings, 'EMAIL_MICROSERVICE_URL', 'https://api.resend.com/emails')
                headers = {
                    'Authorization': f'Bearer {k}',
                    'Content-Type': 'application/json',
                    'User-Agent': 'resend-python/2.0.0'
                }
                resp = requests.post(url, headers=headers, json=p, timeout=12)
                if resp.status_code in (200, 201):
                    print(f"[EMAIL SUCCESS (Resend)]: {resp.status_code} | {resp.text}")
                else:
                    print(f"[EMAIL RESEND RESPONSE {resp.status_code}]: {resp.text}")
                    # If Resend free sandbox rejects because recipient is not account owner (maulikj663@gmail.com)
                    if resp.status_code == 403 and 'maulikj663@gmail.com' not in str(to_addr):
                        print("[EMAIL SANDBOX FALLBACK]: Forwarding copy to maulikj663@gmail.com")
                        fallback_payload = dict(p)
                        fallback_payload['to'] = ['maulikj663@gmail.com']
                        fallback_payload['subject'] = f"[For {to_addr}] {subject}"
                        requests.post(url, headers=headers, json=fallback_payload, timeout=12)
            except Exception as e:
                print(f"[EMAIL ERROR]: {e}")

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
        html = f"""<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:540px;margin:0 auto;padding:28px;border:1px solid #e2e8f0;border-radius:12px;color:#0f172a;">
        <h2 style="color:#2563eb;margin-top:0;font-size:20px;">Verify Your Student Account</h2>
        <p style="color:#475569;font-size:15px;line-height:1.6;">Hello {name},</p>
        <p style="color:#475569;font-size:15px;line-height:1.6;">Thank you for registering on Islington Marketplace. Please confirm your email address to activate your account:</p>
        <p style="margin:26px 0;"><a href="{verify_url}" style="background:#2563eb;color:#ffffff;text-decoration:none;padding:12px 28px;border-radius:8px;font-weight:600;font-size:14px;display:inline-block;">Verify Email Address</a></p>
        <p style="font-size:12px;color:#94a3b8;line-height:1.5;">Direct URL: <a href="{verify_url}" style="color:#2563eb;">{verify_url}</a></p>
        </div>"""
        cls.send_async(u.email, "Verify your Islington Marketplace account", html)

    @classmethod
    def send_admin_new_pending_review_email(cls, p, u, admin_url="https://maulikjoshi.com.np/admin/products/pendingproductreview/"):
        admin_emails = list(User.objects.filter(is_superuser=True).exclude(email='').values_list('email', flat=True))
        if not admin_emails:
            admin_emails = ['maulikj663@gmail.com']
        
        student_name = u.get_full_name() or u.username if u else "Student"
        html = f"""<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:560px;margin:0 auto;padding:28px;border:1px solid #e2e8f0;border-radius:12px;color:#0f172a;">
        <div style="display:inline-block;background:#fef3c7;color:#92400e;padding:4px 10px;border-radius:6px;font-size:12px;font-weight:600;text-transform:uppercase;margin-bottom:12px;">Admin Review Required</div>
        <h2 style="margin:0 0 16px 0;font-size:20px;">New Listing Submitted for Approval</h2>
        <p style="color:#475569;font-size:15px;line-height:1.6;">A new listing has been submitted by <strong>{student_name}</strong> and is awaiting your review.</p>
        <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:16px;margin:18px 0;font-size:14px;color:#334155;line-height:1.7;">
          <div><strong>Product:</strong> {p.name}</div>
          <div><strong>Category:</strong> {p.category.name if p.category else 'General'}</div>
          <div><strong>Price:</strong> Rs. {p.price:.2f}</div>
          <div><strong>Stock:</strong> {p.stock}</div>
          <div><strong>Seller:</strong> {u.email if u else 'N/A'}</div>
        </div>
        <p style="margin:24px 0;">
          <a href="{admin_url}" style="background:#2563eb;color:#ffffff;text-decoration:none;padding:12px 26px;border-radius:8px;font-weight:600;font-size:14px;display:inline-block;">Review in Admin Panel</a>
        </p>
        </div>"""
        cls.send_async(admin_emails, f"Admin Review Required: New listing \"{p.name}\" by {student_name}", html)

    @classmethod
    def send_product_approved_email(cls, u, p, site_url="https://maulikjoshi.com.np"):
        if not u or not u.email: return
        name = u.first_name or u.username
        prod_url = f"{site_url}/products/{p.id}/"
        html = f"""<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:540px;margin:0 auto;padding:28px;border:1px solid #e2e8f0;border-radius:12px;color:#0f172a;">
        <div style="display:inline-block;background:#ecfdf5;color:#065f46;padding:4px 10px;border-radius:6px;font-size:12px;font-weight:600;margin-bottom:12px;">Listing Approved</div>
        <h2 style="margin:0 0 16px 0;font-size:20px;">Your Listing is Live</h2>
        <p style="color:#475569;font-size:15px;line-height:1.6;">Hello {name},</p>
        <p style="color:#475569;font-size:15px;line-height:1.6;">Your listing for <strong>"{p.name}"</strong> has been approved by admin and is now live on Islington Marketplace for <strong>Rs. {p.price:.2f}</strong>.</p>
        <p style="margin:24px 0;"><a href="{prod_url}" style="background:#2563eb;color:#ffffff;text-decoration:none;padding:12px 26px;border-radius:8px;font-weight:600;font-size:14px;display:inline-block;">View Your Item</a></p>
        </div>"""
        cls.send_async(u.email, f"Your listing \"{p.name}\" has been approved", html)

    @classmethod
    def send_product_rejected_email(cls, u, p, reason=""):
        if not u or not u.email: return
        name = u.first_name or u.username
        html = f"""<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:540px;margin:0 auto;padding:28px;border:1px solid #e2e8f0;border-radius:12px;color:#0f172a;">
        <div style="display:inline-block;background:#fef2f2;color:#991b1b;padding:4px 10px;border-radius:6px;font-size:12px;font-weight:600;margin-bottom:12px;">Listing Moderation Notice</div>
        <h2 style="margin:0 0 16px 0;font-size:20px;">Listing Not Approved</h2>
        <p style="color:#475569;font-size:15px;line-height:1.6;">Hello {name},</p>
        <p style="color:#475569;font-size:15px;line-height:1.6;">Your listing for <strong>"{p.name}"</strong> could not be approved at this time.</p>
        {f'<p style="background:#fef2f2;border:1px solid #fecaca;padding:12px;border-radius:8px;color:#991b1b;font-size:14px;"><strong>Reason:</strong> {reason}</p>' if reason else ''}
        <p style="color:#64748b;font-size:13px;line-height:1.5;">Please update your listing details or photos and resubmit from your dashboard.</p>
        </div>"""
        cls.send_async(u.email, f"Listing Update: \"{p.name}\"", html)

    @classmethod
    def send_new_auction_broadcast(cls, auction, auction_url):
        emails = list(User.objects.filter(is_active=True).exclude(email='').values_list('email', flat=True))
        if not emails: return
        html = f"""<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:540px;margin:0 auto;padding:28px;border:1px solid #e2e8f0;border-radius:12px;color:#0f172a;">
        <div style="display:inline-block;background:#fee2e2;color:#991b1b;padding:4px 10px;border-radius:6px;font-size:12px;font-weight:600;margin-bottom:12px;">Live Auction</div>
        <h2 style="margin:0 0 16px 0;font-size:20px;">{auction.title}</h2>
        <p style="color:#475569;font-size:15px;line-height:1.6;">A new 24-hour student auction has started. Starting bid is <strong>Rs. {auction.starting_bid:.2f}</strong>.</p>
        <p style="margin:24px 0;"><a href="{auction_url}" style="background:#2563eb;color:#ffffff;text-decoration:none;padding:12px 26px;border-radius:8px;font-weight:600;font-size:14px;display:inline-block;">Place a Bid</a></p>
        </div>"""
        cls.send_async(emails, f"New 24-Hour Live Auction: {auction.title}", html)

    @classmethod
    def send_outbid_notification(cls, outbid_user, auction, new_bid_amount, auction_url):
        if not outbid_user or not outbid_user.email: return
        name = outbid_user.first_name or outbid_user.username
        html = f"""<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:540px;margin:0 auto;padding:28px;border:1px solid #e2e8f0;border-radius:12px;color:#0f172a;">
        <div style="display:inline-block;background:#fef3c7;color:#92400e;padding:4px 10px;border-radius:6px;font-size:12px;font-weight:600;margin-bottom:12px;">Outbid Notice</div>
        <h2 style="margin:0 0 16px 0;font-size:20px;">You have been outbid on {auction.title}</h2>
        <p style="color:#475569;font-size:15px;line-height:1.6;">Hello {name}, another student has placed a higher bid of <strong>Rs. {new_bid_amount:.2f}</strong>.</p>
        <p style="margin:24px 0;"><a href="{auction_url}" style="background:#2563eb;color:#ffffff;text-decoration:none;padding:12px 26px;border-radius:8px;font-weight:600;font-size:14px;display:inline-block;">Increase Your Bid</a></p>
        </div>"""
        cls.send_async(outbid_user.email, f"Outbid notice: {auction.title}", html)

    @classmethod
    def send_auction_won_notification(cls, winner, seller, auction, site_url="https://maulikjoshi.com.np"):
        if winner and winner.email:
            name = winner.first_name or winner.username
            order_url = f"{site_url}/profile/?tab=orders"
            html = f"""<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:540px;margin:0 auto;padding:28px;border:1px solid #e2e8f0;border-radius:12px;color:#0f172a;">
            <div style="display:inline-block;background:#ecfdf5;color:#065f46;padding:4px 10px;border-radius:6px;font-size:12px;font-weight:600;margin-bottom:12px;">Auction Won</div>
            <h2 style="margin:0 0 16px 0;font-size:20px;">Congratulations {name}</h2>
            <p style="color:#475569;font-size:15px;line-height:1.6;">You won the auction for <strong>{auction.title}</strong> with the winning bid of <strong>Rs. {auction.current_bid:.2f}</strong>.</p>
            <p style="margin:24px 0;"><a href="{order_url}" style="background:#2563eb;color:#ffffff;text-decoration:none;padding:12px 26px;border-radius:8px;font-weight:600;font-size:14px;display:inline-block;">View Order Details</a></p>
            </div>"""
            cls.send_async(winner.email, f"Auction won: {auction.title}", html)

    @classmethod
    def send_order_confirmation_email(cls, order, site_url="https://maulikjoshi.com.np"):
        if not order.buyer_email: return
        html = f"""<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:540px;margin:0 auto;padding:28px;border:1px solid #e2e8f0;border-radius:12px;color:#0f172a;">
        <div style="display:inline-block;background:#eff6ff;color:#1e40af;padding:4px 10px;border-radius:6px;font-size:12px;font-weight:600;margin-bottom:12px;">Order Confirmed</div>
        <h2 style="margin:0 0 16px 0;font-size:20px;">Order #{order.id} Confirmation</h2>
        <p style="color:#475569;font-size:15px;line-height:1.6;">Thank you {order.buyer_name}. Your order total is <strong>Rs. {order.total_amount:.2f}</strong>.</p>
        <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:16px;margin:18px 0;font-size:14px;color:#334155;line-height:1.7;">
          <div><strong>Pickup Location:</strong> {order.meetup_location}</div>
          <div><strong>Pickup Time:</strong> {order.meetup_time}</div>
          <div><strong>Payment Status:</strong> {order.payment_status}</div>
        </div>
        <p style="margin:24px 0;"><a href="{site_url}/profile/?tab=orders" style="background:#2563eb;color:#ffffff;text-decoration:none;padding:12px 26px;border-radius:8px;font-weight:600;font-size:14px;display:inline-block;">View in My Orders</a></p>
        </div>"""
        cls.send_async(order.buyer_email, f"Order #{order.id} Confirmation - Islington Marketplace", html)
