import json, threading, urllib.request, urllib.error
from django.conf import settings

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
    def send_welcome_email(cls, u):
        if u.email: cls.send_async(u.email, f"Welcome to Islington Marketplace, {u.first_name or u.username}!", f"<h2>Welcome {u.first_name or u.username}!</h2><p>Your student account is active. <a href='http://127.0.0.1:8000/profile/?tab=add'>Post a listing</a> to start selling.</p>")

    @classmethod
    def send_product_listed_email(cls, u, p):
        if u.email: cls.send_async(u.email, f'Listing Live: "{p.name}"', f"<h2>Listing Published!</h2><p>Hi {u.first_name or u.username}, your item <strong>{p.name}</strong> is live for Rs. {p.price:.2f}. <a href='http://127.0.0.1:8000/products/{p.id}/'>View Item</a></p>")
