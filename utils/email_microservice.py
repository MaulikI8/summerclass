"""
Email Microservice Client for Islington Marketplace
===================================================
A lightweight, asynchronous, decoupled microservice client for sending transactional
emails (Welcome, Product Published, Inquiry/Chat notifications) via an external HTTP microservice
or REST API (Resend, SendGrid, Brevo, or custom webhook).

Features:
- Non-blocking: Uses daemon background threads so web request latency is 0ms.
- Decoupled: Can point to any external HTTP microservice endpoint.
- Graceful Fallback: If no microservice URL or API key is set, safely logs delivery status in dev mode.
"""

import json
import logging
import threading
import urllib.request
import urllib.error
from django.conf import settings

logger = logging.getLogger(__name__)


class EmailMicroservice:
    """Client for communicating with the Email Microservice."""

    @classmethod
    def get_config(cls):
        return {
            'endpoint': getattr(settings, 'EMAIL_MICROSERVICE_URL', 'https://api.resend.com/emails'),
            'api_key': getattr(settings, 'EMAIL_MICROSERVICE_API_KEY', ''),
            'sender_name': getattr(settings, 'EMAIL_SENDER_NAME', 'Islington Marketplace'),
            'sender_email': getattr(settings, 'EMAIL_SENDER_ADDRESS', 'onboarding@resend.dev'),
            'mock_mode': getattr(settings, 'EMAIL_MICROSERVICE_MOCK', True),
        }

    @classmethod
    def _send_http_request(cls, payload):
        """Dispatches the JSON payload to the external microservice endpoint."""
        config = cls.get_config()

        # If in Mock/Dev mode or no API key is provided, log the event cleanly
        if config['mock_mode'] or not config['api_key']:
            print("\n" + "="*60)
            print("[EMAIL MICROSERVICE DISPATCH - DEV/MOCK MODE]")
            print(f"To: {payload.get('to')}")
            print(f"Subject: {payload.get('subject')}")
            print(f"Sender: {payload.get('from')}")
            print("Payload summary:")
            print(json.dumps({k: v for k, v in payload.items() if k != 'html'}, indent=2))
            print("="*60 + "\n")
            return {'status': 'success', 'mode': 'mock', 'delivered': True}

        try:
            req_data = json.dumps(payload).encode('utf-8')
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f"Bearer {config['api_key']}",
                'User-Agent': 'IslingtonMarketplace-EmailMicroservice/1.0',
            }
            req = urllib.request.Request(config['endpoint'], data=req_data, headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=10) as response:
                res_body = response.read().decode('utf-8')
                logger.info(f"Email microservice response: {res_body}")
                return {'status': 'success', 'response': res_body}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode('utf-8')
            logger.error(f"Email microservice HTTP Error {e.code}: {err_body}")
            return {'status': 'error', 'code': e.code, 'detail': err_body}
        except Exception as ex:
            logger.error(f"Email microservice Connection Error: {str(ex)}")
            return {'status': 'error', 'detail': str(ex)}

    @classmethod
    def send_async(cls, recipient_email, subject, html_content, text_content=None):
        """Asynchronously dispatches an email in a background worker thread."""
        if not recipient_email:
            return

        config = cls.get_config()
        from_header = f"{config['sender_name']} <{config['sender_email']}>"

        payload = {
            'from': from_header,
            'to': [recipient_email] if isinstance(recipient_email, str) else recipient_email,
            'subject': subject,
            'html': html_content,
            'text': text_content or subject,
        }

        # Fire and forget in a separate thread so page response is instantaneous
        worker = threading.Thread(target=cls._send_http_request, args=(payload,), daemon=True)
        worker.start()

    # =========================================================================
    # PRE-BUILT TRANSACTIONAL EMAIL TEMPLATES
    # =========================================================================

    @classmethod
    def send_welcome_email(cls, user):
        """Dispatches student welcome onboarding email via microservice."""
        if not user.email:
            return

        name = user.first_name or user.username
        subject = f"Welcome to Islington Marketplace, {name}!"
        html = f"""
        <div style="font-family: 'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden;">
            <div style="background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%); padding: 32px 24px; text-align: center; color: #ffffff;">
                <h1 style="margin: 0; font-size: 24px; font-weight: 700;">Welcome to Islington Marketplace</h1>
                <p style="margin: 8px 0 0; font-size: 14px; opacity: 0.9;">The official campus platform for student creators and trade</p>
            </div>
            <div style="padding: 32px 24px; color: #1e293b; line-height: 1.6;">
                <h2 style="font-size: 18px; margin-top: 0;">Hi {name},</h2>
                <p>Your student account has been successfully created! You can now explore student businesses, order custom creations, or list your own products to sell to fellow peers on campus.</p>
                
                <div style="background: #f8fafc; border-left: 4px solid #2563eb; padding: 16px; border-radius: 6px; margin: 24px 0;">
                    <strong style="color: #0f172a;">What you can do right now:</strong>
                    <ul style="margin: 8px 0 0; padding-left: 20px; color: #475569; font-size: 14px;">
                        <li>Post your products directly from your Student Dashboard</li>
                        <li>Chat with student sellers via the live campus messenger</li>
                        <li>Save favorites to your wishlist and track your sales</li>
                    </ul>
                </div>

                <div style="text-align: center; margin: 32px 0;">
                    <a href="http://127.0.0.1:8000/profile/?tab=add" style="background: #2563eb; color: #ffffff; text-decoration: none; padding: 12px 28px; border-radius: 30px; font-weight: 600; font-size: 15px; display: inline-block;">Post Your First Listing</a>
                </div>

                <p style="font-size: 13px; color: #64748b; margin-bottom: 0;">Happy trading,<br><strong>Islington Student Marketplace Team</strong></p>
            </div>
        </div>
        """
        cls.send_async(user.email, subject, html)

    @classmethod
    def send_product_listed_email(cls, user, product):
        """Dispatches product publication confirmation email via microservice."""
        if not user.email:
            return

        name = user.first_name or user.username
        subject = f'Your product "{product.name}" is now live on Islington Marketplace!'
        html = f"""
        <div style="font-family: 'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden;">
            <div style="background: linear-gradient(135deg, #059669 0%, #10b981 100%); padding: 28px 24px; text-align: center; color: #ffffff;">
                <h1 style="margin: 0; font-size: 22px; font-weight: 700;">Listing Published Successfully</h1>
                <p style="margin: 6px 0 0; font-size: 14px; opacity: 0.95;">Your product is now visible to all Islington students</p>
            </div>
            <div style="padding: 28px 24px; color: #1e293b; line-height: 1.6;">
                <h2 style="font-size: 17px; margin-top: 0;">Hello {name},</h2>
                <p>Great news! Your product <strong>"{product.name}"</strong> is live on the marketplace.</p>
                
                <table style="width: 100%; border-collapse: collapse; margin: 20px 0; background: #f8fafc; border-radius: 8px; overflow: hidden;">
                    <tr>
                        <td style="padding: 12px 16px; border-bottom: 1px solid #e2e8f0; font-weight: 600; color: #64748b; width: 35%;">Category:</td>
                        <td style="padding: 12px 16px; border-bottom: 1px solid #e2e8f0; font-weight: 600; color: #0f172a;">{product.category.name}</td>
                    </tr>
                    <tr>
                        <td style="padding: 12px 16px; border-bottom: 1px solid #e2e8f0; font-weight: 600; color: #64748b;">Listed Price:</td>
                        <td style="padding: 12px 16px; border-bottom: 1px solid #e2e8f0; font-weight: 700; color: #2563eb;">Rs. {product.price:.2f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 12px 16px; font-weight: 600; color: #64748b;">Available Stock:</td>
                        <td style="padding: 12px 16px; font-weight: 600; color: #059669;">{product.stock} units</td>
                    </tr>
                </table>

                <div style="text-align: center; margin: 28px 0;">
                    <a href="http://127.0.0.1:8000/products/{product.id}/" style="background: #2563eb; color: #ffffff; text-decoration: none; padding: 11px 24px; border-radius: 25px; font-weight: 600; font-size: 14px; display: inline-block;">View Product Page</a>
                </div>
            </div>
        </div>
        """
        cls.send_async(user.email, subject, html)
