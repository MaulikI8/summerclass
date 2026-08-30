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
    def _send(cls, recipients, subject, html):
        if not recipients:
            return False
        r = [e.strip() for e in (recipients if isinstance(recipients, list) else [recipients]) if e and '@' in str(e)]
        if not r:
            return False

        user = getattr(settings, 'EMAIL_HOST_USER', 'maulikj663@gmail.com')
        pwd = getattr(settings, 'EMAIL_HOST_PASSWORD', 'lwdtdidnicnudkxr')
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

            m.attach(MIMEText("Please view in an HTML compatible email client.", 'plain', 'utf-8'))
            m.attach(MIMEText(html, 'html', 'utf-8'))
            return m

        # Strategy 1: Fast TLS SMTP to Gmail (Port 587, timeout=4s)
        try:
            m = build_message()
            with smtplib.SMTP('smtp.gmail.com', 587, timeout=4) as s:
                s.starttls()
                s.login(user, pwd)
                s.send_message(m, from_addr=user, to_addrs=r)
            logger.info(f"Instant TLS email sent to {r}")
            return True
        except Exception as e:
            logger.warning(f"SMTP TLS 587 failed ({e}), trying SSL 465 fallback...")

        # Strategy 2: SSL SMTP to Gmail (Port 465, timeout=4s)
        try:
            m = build_message()
            with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=4) as s:
                s.login(user, pwd)
                s.send_message(m, from_addr=user, to_addrs=r)
            logger.info(f"Instant SSL email sent to {r}")
            return True
        except Exception as e:
            logger.warning(f"SMTP_SSL 465 failed ({e}), trying Django EmailMultiAlternatives fallback...")

        # Strategy 3: Django core mail backend fallback
        try:
            msg = EmailMultiAlternatives(subject, "Please view in HTML.", from_hdr, r)
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
    def send_sync(cls, to, sub, html):
        """Sends email synchronously."""
        return cls._send(to, sub, html)

    @classmethod
    def send_async(cls, to, sub, html):
        """Dispatches email via managed thread pool for sub-second web UI response and instant background sending."""
        if not to:
            return False
        _EXECUTOR.submit(cls._send, to, sub, html)
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
        b = f"""<p>Hello <strong>{u.first_name or u.username}</strong>,</p><p>Your 6-digit verification code is:</p>
        <div style="background:#f8fafc;border:2px dashed #3b82f6;border-radius:10px;padding:16px;text-align:center;margin:16px 0;"><span style="font-size:32px;font-weight:800;letter-spacing:8px;color:#1d4ed8;font-family:monospace;">{code}</span></div>
        <p style="font-size:12px;color:#64748b;">Expires in 10 minutes.</p>"""
        return cls.send_async(u.email, f"Your Verification Code: {code}", cls._wrap("Account Verification", "Security OTP", b))

    @classmethod
    def send_activation_email(cls, u, activation_url):
        if not u or not u.email: return False
        b = f"""<p>Hello <strong>{u.first_name or u.username}</strong>,</p>
        <p>Thank you for registering at Islington Marketplace! Please click the button below to activate your student account:</p>
        <div style="text-align:center;margin:24px 0;">
            <a href="{activation_url}" style="background:#4F46E5;color:#ffffff;padding:12px 28px;border-radius:30px;text-decoration:none;font-weight:bold;display:inline-block;">Activate My Account &rarr;</a>
        </div>
        <p style="font-size:12px;color:#64748b;">If the button above does not work, copy and paste this link into your browser:<br/><a href="{activation_url}" style="color:#4F46E5;">{activation_url}</a></p>"""
        return cls.send_async(u.email, "Activate Your Islington Marketplace Account", cls._wrap("Account Verification", "Email Verification Link", b))

    @classmethod
    def send_order_confirmation_email(cls, order, site_url=""):
        if not order.buyer_email: return False
        items = "".join([f"<li>{i.quantity}x {i.product_name} — Rs. {i.price:.2f}</li>" for i in order.items.all()])
        b = f"""<p>Hello <strong>{order.buyer_name}</strong>,</p><p>Your order #{order.id} is confirmed!</p>
        <ul>{items}</ul><p><strong>Total: Rs. {order.total_amount:.2f}</strong></p><p>📍 Location: {order.meetup_location}</p>"""
        return cls.send_async(order.buyer_email, f"Order Confirmed #{order.id}", cls._wrap(f"Order #{order.id} Confirmed", "Order Receipt", b))

    @classmethod
    def send_seller_new_order_email(cls, seller, product, order, qty=1, site_url=""):
        if not seller or not seller.email: return False
        b = f"""<p>Hello <strong>{seller.first_name or seller.username}</strong>,</p>
        <p><strong>{order.buyer_name}</strong> purchased <strong>{qty}x {product.name}</strong>!</p>
        <p>Buyer Phone: {order.buyer_phone} | Location: {order.meetup_location}</p>"""
        return cls.send_async(seller.email, f"New Order for {product.name}!", cls._wrap("New Sale Alert", "Student Sale", b))

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
