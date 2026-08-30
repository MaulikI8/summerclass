import smtplib, logging
from concurrent.futures import ThreadPoolExecutor
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)

# Managed thread pool executor for fast background dispatch
_EXECUTOR = ThreadPoolExecutor(max_workers=6, thread_name_prefix='email_dispatch_')

class EmailMicroservice:
    @classmethod
    def _send(cls, recipients, subject, html, text_body=None):
        if not recipients:
            return False
        r = [e.strip() for e in (recipients if isinstance(recipients, list) else [recipients]) if e and '@' in str(e)]
        if not r:
            return False

        user = (getattr(settings, 'EMAIL_HOST_USER', '') or 'maulikj663@gmail.com').strip()
        pwd = (getattr(settings, 'EMAIL_HOST_PASSWORD', '') or 'lwdtdidnicnudkxr').strip()
        from_hdr = f"Islington Marketplace <{user}>"

        def build_message():
            m = MIMEMultipart('alternative')
            m['Subject'] = subject
            m['From'] = from_hdr
            m['To'] = ', '.join(r)
            m['Date'] = formatdate(localtime=True)
            m['Message-ID'] = make_msgid()
            m['Reply-To'] = user
            
            # Transactional High Priority Headers for Instant Inbox Delivery
            m['X-Priority'] = '1'
            m['Priority'] = 'urgent'
            m['Importance'] = 'high'
            m['X-MSMail-Priority'] = 'High'
            m['Auto-Submitted'] = 'auto-generated'

            plain_content = text_body or "Please view this message in an HTML compatible email client."
            m.attach(MIMEText(plain_content, 'plain', 'utf-8'))
            m.attach(MIMEText(html, 'html', 'utf-8'))
            return m

        # Strategy 1: Fast SSL SMTP to Gmail (Port 465, timeout=6s - ideal for cloud hosting like Render)
        try:
            m = build_message()
            with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=6) as s:
                s.login(user, pwd)
                s.send_message(m, from_addr=user, to_addrs=r)
            logger.info(f"Instant SSL email sent to {r}")
            return True
        except Exception as e:
            logger.warning(f"SMTP_SSL 465 failed ({e}), trying TLS 587 fallback...")

        # Strategy 2: TLS SMTP to Gmail (Port 587, timeout=6s)
        try:
            m = build_message()
            with smtplib.SMTP('smtp.gmail.com', 587, timeout=6) as s:
                s.starttls()
                s.login(user, pwd)
                s.send_message(m, from_addr=user, to_addrs=r)
            logger.info(f"Instant TLS email sent to {r}")
            return True
        except Exception as e:
            logger.warning(f"SMTP TLS 587 failed ({e}), trying Django EmailMultiAlternatives fallback...")

        # Strategy 3: Django core mail backend fallback
        try:
            plain_content = text_body or "Please view in HTML format."
            msg = EmailMultiAlternatives(subject, plain_content, from_hdr, r)
            msg.extra_headers = {
                'X-Priority': '1',
                'Priority': 'urgent',
                'Importance': 'high'
            }
            msg.attach_alternative(html, "text/html")
            res = msg.send(fail_silently=False)
            return bool(res)
        except Exception as e:
            logger.error(f"All email dispatch strategies failed for {r}: {e}")
            return False

    @classmethod
    def send_sync(cls, to, sub, html, text_body=None):
        """Sends email synchronously."""
        return cls._send(to, sub, html, text_body=text_body)

    @classmethod
    def send_async(cls, to, sub, html, text_body=None):
        """Dispatches email via managed thread pool for sub-second web UI response and instant background sending."""
        if not to:
            return False
        _EXECUTOR.submit(cls._send, to, sub, html, text_body=text_body)
        return True

    @staticmethod
    def _wrap(title, badge, body):
        return f"""<div style="font-family:sans-serif;max-width:520px;margin:0 auto;padding:28px;border:1px solid #e2e8f0;border-radius:12px;color:#0f172a;background:#ffffff;">
        <div style="background:#eff6ff;color:#2563eb;padding:4px 10px;border-radius:6px;font-size:12px;font-weight:700;display:inline-block;margin-bottom:12px;">{badge}</div>
        <h2 style="margin:0 0 16px;font-size:20px;color:#1e3a8a;">{title}</h2>{body}
        <div style="margin-top:24px;padding-top:12px;border-top:1px solid #e2e8f0;font-size:12px;color:#94a3b8;text-align:center;">Islington Marketplace • Kamalpokhari, Kathmandu</div></div>"""

    @classmethod
    def send_otp_email(cls, u, code):
        if not u or not u.email: return False
        text = f"Hello {u.first_name or u.username},\n\nYour 6-digit Islington Marketplace verification code is: {code}\n\nThis code expires in 10 minutes."
        b = f"""<p>Hello <strong>{u.first_name or u.username}</strong>,</p><p>Your 6-digit verification code is:</p>
        <div style="background:#f8fafc;border:2px dashed #3b82f6;border-radius:10px;padding:16px;text-align:center;margin:16px 0;"><span style="font-size:32px;font-weight:800;letter-spacing:8px;color:#1d4ed8;font-family:monospace;">{code}</span></div>
        <p style="font-size:12px;color:#64748b;">Expires in 10 minutes.</p>"""
        return cls.send_async(u.email, f"Your Verification Code: {code}", cls._wrap("Account Verification", "Security OTP", b), text_body=text)

    @classmethod
    def send_activation_email(cls, u, activation_url):
        if not u or not u.email: return False
        if 'http://' in activation_url and not ('127.0.0.1' in activation_url or 'localhost' in activation_url):
            activation_url = activation_url.replace('http://', 'https://')
        name = u.first_name or u.username
        text = f"Hello {name},\n\nThank you for registering at Islington Marketplace! Please use the following link to activate your student account:\n\n{activation_url}\n\nIslington Marketplace Team"
        b = f"""<p>Hello <strong>{name}</strong>,</p>
        <p>Thank you for registering at Islington Marketplace! Please click the button below to activate your student account:</p>
        <div style="text-align:center;margin:24px 0;">
            <a href="{activation_url}" style="background:#4F46E5;color:#ffffff;padding:12px 28px;border-radius:30px;text-decoration:none;font-weight:bold;display:inline-block;">Activate My Account &rarr;</a>
        </div>
        <p style="font-size:12px;color:#64748b;">If the button above does not work, copy and paste this link into your browser:<br/><a href="{activation_url}" style="color:#4F46E5;">{activation_url}</a></p>"""
        return cls.send_sync(u.email, "Activate Your Islington Marketplace Account", cls._wrap("Account Verification", "Email Verification Link", b), text_body=text)

    @classmethod
    def send_order_confirmation_email(cls, order, site_url=""):
        if not order.buyer_email: return False
        items_html = "".join([
            f"<tr style='border-bottom:1px solid #f1f5f9;'>"
            f"<td style='padding:10px 0;color:#334155;font-weight:600;'>{i.quantity}x {i.product_name}</td>"
            f"<td style='padding:10px 0;text-align:right;color:#0f172a;font-weight:700;'>Rs. {i.price:.2f}</td>"
            f"</tr>" for i in order.items.all()
        ])
        b = f"""
        <p style="font-size:15px;color:#334155;margin-bottom:16px;">Hello <strong>{order.buyer_name}</strong>,</p>
        <p style="font-size:14px;color:#334155;">Your payment has been authorized via <strong>Khalti Digital Gateway</strong> and your order <strong>#{order.id}</strong> is confirmed!</p>
        
        <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:16px;margin:20px 0;">
            <h4 style="margin:0 0 12px;color:#1e3a8a;font-size:14px;text-transform:uppercase;letter-spacing:0.5px;">Order Summary</h4>
            <table style="width:100%;border-collapse:collapse;font-size:14px;">
                <tbody>{items_html}</tbody>
            </table>
            <div style="margin-top:12px;padding-top:12px;border-top:2px solid #e2e8f0;display:flex;justify-content:space-between;">
                <span style="font-size:15px;font-weight:700;color:#1e293b;">Total Amount Paid:</span>
                <span style="font-size:16px;font-weight:800;color:#5c2d91;">Rs. {order.total_amount:.2f}</span>
            </div>
        </div>

        <div style="background:#faf5ff;border-left:4px solid #5c2d91;padding:12px 16px;border-radius:0 8px 8px 0;margin-bottom:20px;">
            <p style="margin:0 0 4px;font-size:13px;color:#5c2d91;font-weight:700;">📍 Pickup Location: {order.meetup_location}</p>
            <p style="margin:0;font-size:13px;color:#6b21a8;">⏰ Preferred Time: {order.meetup_time}</p>
        </div>

        <p style="font-size:12px;color:#64748b;margin-top:24px;text-align:center;">Thank you for supporting campus commerce at Islington Student Marketplace!</p>
        """
        return cls.send_async(order.buyer_email, f"✅ Order Confirmed #{order.id} • Islington Marketplace", cls._wrap(f"Order #{order.id} Confirmed", "Khalti Payment Successful", b))

    @classmethod
    def send_seller_new_order_email(cls, seller, product, order, qty=1, site_url=""):
        if not seller or not seller.email: return False
        b = f"""
        <p style="font-size:15px;color:#334155;margin-bottom:16px;">Hello <strong>{seller.first_name or seller.username}</strong>,</p>
        <p style="font-size:14px;color:#334155;">Great news! <strong>{order.buyer_name}</strong> just purchased <strong>{qty}x {product.name}</strong> on Islington Marketplace!</p>
        
        <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;padding:16px;margin:20px 0;">
            <h4 style="margin:0 0 8px;color:#166534;font-size:14px;">Buyer Details &amp; Pickup Logistics</h4>
            <p style="margin:4px 0;font-size:13px;color:#15803d;">👤 <strong>Buyer Name:</strong> {order.buyer_name}</p>
            <p style="margin:4px 0;font-size:13px;color:#15803d;">📞 <strong>Buyer Phone:</strong> {order.buyer_phone}</p>
            <p style="margin:4px 0;font-size:13px;color:#15803d;">📧 <strong>Buyer Email:</strong> {order.buyer_email}</p>
            <p style="margin:4px 0;font-size:13px;color:#15803d;">📍 <strong>Meetup Spot:</strong> {order.meetup_location}</p>
            <p style="margin:4px 0;font-size:13px;color:#15803d;">⏰ <strong>Meetup Time:</strong> {order.meetup_time}</p>
        </div>
        """
        return cls.send_async(seller.email, f"🎉 New Sale: {product.name}!", cls._wrap("New Sale Alert", "Student Marketplace Sale", b))

    @classmethod
    def send_product_approved_email(cls, seller, product, site_url=""):
        if not seller or not seller.email: return False
        b = f"""<p>Hello <strong>{seller.first_name or seller.username}</strong>,</p><p>Your listing <strong>'{product.name}'</strong> has been approved by admin and is now live on the marketplace!</p>"""
        return cls.send_async(seller.email, f"Listing Approved: {product.name}", cls._wrap("Listing Approved", "Item Live", b))

    @classmethod
    def send_product_rejected_email(cls, seller, product, reason=""):
        if not seller or not seller.email: return False
        b = f"""<p>Hello <strong>{seller.first_name or seller.username}</strong>,</p><p>Your listing '{product.name}' was not approved.</p><p>Reason: {reason or 'Item did not meet guidelines.'}</p>"""
        return cls.send_async(seller.email, f"Listing Update: {product.name}", cls._wrap("Listing Update", "Moderation Notice", b))

    @classmethod
    def send_admin_new_pending_review_email(cls, product, seller, admin_url=""):
        b = f"""<p>Student <strong>{seller.username}</strong> submitted a new listing: <strong>{product.name}</strong> (Rs. {product.price:.2f}).</p>"""
        emails = list(User.objects.filter(is_superuser=True).exclude(email='').values_list('email', flat=True)) or ['maulikj663@gmail.com']
        return cls.send_async(emails, f"Review Required: {product.name}", cls._wrap("Moderation Notice", "Admin Action", b))

    @classmethod
    def send_new_auction_broadcast(cls, auction, link=""):
        b = f"""<p>A new 24-hour live auction for <strong>{auction.title}</strong> has started at starting bid <strong>Rs. {auction.start_bid:.2f}</strong>!</p>"""
        emails = list(User.objects.exclude(email='').values_list('email', flat=True))
        return cls.send_async(emails, f"🔥 Live Auction: {auction.title}", cls._wrap("Live Auction", "Campus Auction", b))

    @classmethod
    def send_outbid_notification(cls, user, auction, new_bid_amount, link=""):
        if not user or not user.email: return False
        b = f"""<p>Hello <strong>{user.first_name or user.username}</strong>,</p><p>You have been outbid on <strong>{auction.title}</strong>! The new highest bid is <strong>Rs. {new_bid_amount:.2f}</strong>.</p>"""
        return cls.send_async(user.email, f"Outbid Alert: {auction.title}", cls._wrap("Outbid Alert", "Auction Update", b))

    @classmethod
    def send_auction_won_notification(cls, winner, seller, auction):
        if not winner or not winner.email: return False
        b = f"""<p>Congratulations <strong>{winner.first_name or winner.username}</strong>!</p><p>Your winning bid of <strong>Rs. {auction.current_bid:.2f}</strong> for <strong>{auction.title}</strong> was accepted by {seller.username}.</p>"""
        return cls.send_async(winner.email, f"🎉 Auction Won: {auction.title}", cls._wrap("Auction Won", "Winning Bid", b))
