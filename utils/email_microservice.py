import json, threading, urllib.request
from django.conf import settings

class EmailMicroservice:
    @classmethod
    def _send(cls, p):
        k = getattr(settings, 'EMAIL_MICROSERVICE_API_KEY', '')
        if getattr(settings, 'EMAIL_MICROSERVICE_MOCK', True) or not k:
            print(f"[EMAIL MICROSERVICE] To: {p.get('to')} | Subject: {p.get('subject')}")
            return
        try:
            req = urllib.request.Request(getattr(settings, 'EMAIL_MICROSERVICE_URL', 'https://api.resend.com/emails'), data=json.dumps(p).encode(), headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {k}'}, method='POST')
            urllib.request.urlopen(req, timeout=8)
        except Exception as e: print(f"[EMAIL ERROR] {e}")

    @classmethod
    def send_async(cls, to, sub, html):
        if not to: return
        p = {'from': f"{getattr(settings, 'EMAIL_SENDER_NAME', 'Islington Marketplace')} <{getattr(settings, 'EMAIL_SENDER_ADDRESS', 'onboarding@resend.dev')}>", 'to': [to] if isinstance(to, str) else to, 'subject': sub, 'html': html}
        threading.Thread(target=cls._send, args=(p,), daemon=True).start()

    @classmethod
    def send_welcome_email(cls, u):
        if u.email: cls.send_async(u.email, f"Welcome to Islington Marketplace, {u.first_name or u.username}!", f"<h2>Welcome {u.first_name or u.username}!</h2><p>Your student account is active. <a href='http://127.0.0.1:8000/profile/?tab=add'>Post a listing</a> to start selling.</p>")

    @classmethod
    def send_product_listed_email(cls, u, p):
        if u.email: cls.send_async(u.email, f'Listing Live: "{p.name}"', f"<h2>Listing Published!</h2><p>Hi {u.first_name or u.username}, your item <strong>{p.name}</strong> is live for Rs. {p.price:.2f}. <a href='http://127.0.0.1:8000/products/{p.id}/'>View Item</a></p>")
