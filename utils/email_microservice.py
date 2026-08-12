import json, logging, threading, urllib.request, urllib.error
from django.conf import settings

logger = logging.getLogger(__name__)

class EmailMicroservice:
    @classmethod
    def _send(cls, payload):
        mock = getattr(settings, 'EMAIL_MICROSERVICE_MOCK', True)
        api_key = getattr(settings, 'EMAIL_MICROSERVICE_API_KEY', '')
        if mock or not api_key:
            print(f"[EMAIL MICROSERVICE] To: {payload.get('to')} | Subject: {payload.get('subject')}")
            return {'status': 'success', 'mode': 'mock'}
        try:
            url = getattr(settings, 'EMAIL_MICROSERVICE_URL', 'https://api.resend.com/emails')
            req = urllib.request.Request(
                url, data=json.dumps(payload).encode(),
                headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'},
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                return {'status': 'success', 'body': r.read().decode()}
        except Exception as e:
            logger.error(f"Email microservice error: {e}")
            return {'status': 'error', 'detail': str(e)}

    @classmethod
    def send_async(cls, to_email, subject, html):
        if not to_email:
            return
        sender = f"{getattr(settings, 'EMAIL_SENDER_NAME', 'Islington Marketplace')} <{getattr(settings, 'EMAIL_SENDER_ADDRESS', 'onboarding@resend.dev')}>"
        payload = {'from': sender, 'to': [to_email] if isinstance(to_email, str) else to_email, 'subject': subject, 'html': html, 'text': subject}
        threading.Thread(target=cls._send, args=(payload,), daemon=True).start()

    @classmethod
    def send_welcome_email(cls, user):
        if not user.email: return
        name = user.first_name or user.username
        html = f"""<div style="font-family:sans-serif;max-width:560px;margin:0 auto;padding:24px;border:1px solid #e2e8f0;border-radius:10px;">
        <h2 style="color:#2563eb;margin-top:0;">Welcome to Islington Marketplace, {name}!</h2>
        <p>Your student account is active. You can now explore student businesses or list items to sell on campus.</p>
        <p><a href="http://127.0.0.1:8000/profile/?tab=add" style="background:#2563eb;color:#fff;padding:10px 20px;border-radius:20px;text-decoration:none;font-weight:bold;display:inline-block;">Post a Listing</a></p>
        </div>"""
        cls.send_async(user.email, f"Welcome to Islington Marketplace, {name}!", html)

    @classmethod
    def send_product_listed_email(cls, user, product):
        if not user.email: return
        name = user.first_name or user.username
        html = f"""<div style="font-family:sans-serif;max-width:560px;margin:0 auto;padding:24px;border:1px solid #e2e8f0;border-radius:10px;">
        <h2 style="color:#059669;margin-top:0;">Listing Published!</h2>
        <p>Hi {name}, your item <strong>{product.name}</strong> is now live on the marketplace for <strong>Rs. {product.price:.2f}</strong>.</p>
        <p><a href="http://127.0.0.1:8000/products/{product.id}/" style="background:#2563eb;color:#fff;padding:10px 20px;border-radius:20px;text-decoration:none;font-weight:bold;display:inline-block;">View Product</a></p>
        </div>"""
        cls.send_async(user.email, f'Listing Live: "{product.name}"', html)
