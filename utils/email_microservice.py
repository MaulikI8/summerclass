import threading, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.contrib.auth.models import User

class EmailMicroservice:
    @classmethod
    def _send(cls, recipients, subject, html):
        if not recipients: return
        r = [e.strip() for e in (recipients if isinstance(recipients, list) else [recipients]) if e and '@' in str(e)]
        if not r: return
        user = getattr(settings, 'EMAIL_HOST_USER', 'maulikj663@gmail.com')
        pwd = getattr(settings, 'EMAIL_HOST_PASSWORD', 'lwdtdidnicnudkxr')
        from_hdr = f"Islington Marketplace <{user}>"
        
        try:
            m = MIMEMultipart('alternative')
            m['Subject'], m['From'], m['To'] = subject, from_hdr, ', '.join(r)
            m['Date'], m['Message-ID'], m['Reply-To'] = formatdate(localtime=True), make_msgid(), user
            m.attach(MIMEText("Please view in HTML client.", 'plain', 'utf-8'))
            m.attach(MIMEText(html, 'html', 'utf-8'))
            with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=8) as s:
                s.login(user, pwd)
                s.send_message(m, from_addr=user, to_addrs=r)
            return
        except Exception:
            try:
                msg = EmailMultiAlternatives(subject, "Please view in HTML.", from_hdr, r)
                msg.attach_alternative(html, "text/html")
                msg.send(fail_silently=True)
            except Exception: pass

    @classmethod
    def send_async(cls, to, sub, html):
        if to: threading.Thread(target=cls._send, args=(to, sub, html), daemon=True).start()

    @staticmethod
    def _wrap(title, badge, body):
        return f"""<div style="font-family:sans-serif;max-width:520px;margin:0 auto;padding:28px;border:1px solid #e2e8f0;border-radius:12px;color:#0f172a;">
        <div style="background:#eff6ff;color:#2563eb;padding:4px 10px;border-radius:6px;font-size:12px;font-weight:700;display:inline-block;margin-bottom:12px;">{badge}</div>
        <h2 style="margin:0 0 16px;font-size:20px;color:#1e3a8a;">{title}</h2>{body}
        <div style="margin-top:24px;padding-top:12px;border-top:1px solid #e2e8f0;font-size:12px;color:#94a3b8;text-align:center;">Islington Marketplace • Kamalpokhari, Kathmandu</div></div>"""

    @classmethod
    def send_otp_email(cls, u, code):
        if not u or not u.email: return
        b = f"""<p>Hello <strong>{u.first_name or u.username}</strong>,</p><p>Your 6-digit verification code is:</p>
        <div style="background:#f8fafc;border:2px dashed #3b82f6;border-radius:10px;padding:16px;text-align:center;margin:16px 0;"><span style="font-size:32px;font-weight:800;letter-spacing:8px;color:#1d4ed8;font-family:monospace;">{code}</span></div>
        <p style="font-size:12px;color:#64748b;">Expires in 10 minutes.</p>"""
        cls.send_async(u.email, f"Your Verification Code: {code}", cls._wrap("Account Verification", "Security OTP", b))

    @classmethod
    def send_order_confirmation_email(cls, order, site_url=""):
        if not order.buyer_email: return
        items = "".join([f"<li>{i.quantity}x {i.product_name} — Rs. {i.price:.2f}</li>" for i in order.items.all()])
        b = f"""<p>Hello <strong>{order.buyer_name}</strong>,</p><p>Your order #{order.id} is confirmed!</p>
        <ul>{items}</ul><p><strong>Total: Rs. {order.total_amount:.2f}</strong></p><p>📍 Location: {order.meetup_location}</p>"""
        cls.send_async(order.buyer_email, f"Order Confirmed #{order.id}", cls._wrap(f"Order #{order.id} Confirmed", "Order Receipt", b))

    @classmethod
    def send_seller_new_order_email(cls, seller, product, order, qty=1, site_url=""):
        if not seller or not seller.email: return
        b = f"""<p>Hello <strong>{seller.first_name or seller.username}</strong>,</p>
        <p><strong>{order.buyer_name}</strong> purchased <strong>{qty}x {product.name}</strong>!</p>
        <p>Buyer Phone: {order.buyer_phone} | Location: {order.meetup_location}</p>"""
        cls.send_async(seller.email, f"New Order for {product.name}!", cls._wrap("New Sale Alert", "Student Sale", b))

    @classmethod
    def send_product_approved_email(cls, seller, product, site_url=""):
        if not seller or not seller.email: return
        b = f"""<p>Hello <strong>{seller.first_name or seller.username}</strong>,</p><p>Your listing <strong>'{product.name}'</strong> has been approved by admin and is now live on the marketplace!</p>"""
        cls.send_async(seller.email, f"Listing Approved: {product.name}", cls._wrap("Listing Approved", "Item Live", b))

    @classmethod
    def send_product_rejected_email(cls, seller, product, reason=""):
        if not seller or not seller.email: return
        b = f"""<p>Hello <strong>{seller.first_name or seller.username}</strong>,</p><p>Your listing '{product.name}' was not approved.</p><p>Reason: {reason or 'Item did not meet guidelines.'}</p>"""
        cls.send_async(seller.email, f"Listing Update: {product.name}", cls._wrap("Listing Update", "Moderation Notice", b))

    @classmethod
    def send_admin_new_pending_review_email(cls, product, seller, admin_url=""):
        b = f"""<p>Student <strong>{seller.username}</strong> submitted a new listing: <strong>{product.name}</strong> (Rs. {product.price:.2f}).</p>"""
        emails = list(User.objects.filter(is_superuser=True).exclude(email='').values_list('email', flat=True)) or ['maulikj663@gmail.com']
        cls.send_async(emails, f"Review Required: {product.name}", cls._wrap("Moderation Notice", "Admin Action", b))

    @classmethod
    def send_new_auction_broadcast(cls, auction, auction_url=""):
        b = f"""<p>New live 24h auction: <strong>{auction.title}</strong> starting at Rs. {auction.starting_bid:.2f}!</p>"""
        emails = list(User.objects.filter(is_active=True).exclude(email='').values_list('email', flat=True))
        cls.send_async(emails, f"Live Auction: {auction.product.name}", cls._wrap("24h Live Auction", "Campus Auction", b))

    @classmethod
    def send_outbid_notification(cls, user, auction, new_bid, auction_url=""):
        if not user or not user.email: return
        b = f"""<p>You have been outbid on <strong>{auction.product.name}</strong>. New highest bid: <strong>Rs. {new_bid:.2f}</strong>.</p>"""
        cls.send_async(user.email, f"Outbid: {auction.product.name}", cls._wrap("Outbid Alert", "Auction Update", b))

    @classmethod
    def send_auction_won_notification(cls, winner, seller, auction):
        if winner and winner.email:
            b = f"""<p>Congratulations <strong>{winner.username}</strong>! You won the auction for <strong>{auction.title}</strong> at Rs. {auction.current_bid:.2f}!</p>"""
            cls.send_async(winner.email, f"Auction Won: {auction.title}", cls._wrap("You Won!", "Auction Winner", b))
