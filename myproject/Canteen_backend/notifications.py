import json
import logging
import threading
import urllib.request
import urllib.error
from django.conf import settings
from .models import Order

logger = logging.getLogger(__name__)


def build_order_ready_html(order, items):
    """
    Renders a responsive, clean HTML email template for orders ready for pickup.
    """
    user_name = order.user.first_name or order.user.username or "Student"
    canteen_name = order.canteen.name if order.canteen else "Main Canteen"
    canteen_location = (order.canteen.location if order.canteen and order.canteen.location else "Amrita Campus")

    items_rows_html = ""
    for item in items:
        prod_name = item.product.name if item.product else "Item"
        item_qty = item.quantity
        item_price = f"₹ {(item.price * item_qty):.2f}"
        items_rows_html += f"""
        <tr>
            <td style="padding: 10px 12px; border-bottom: 1px solid #f0f0f0; color: #333; font-size: 14px;">{prod_name}</td>
            <td style="padding: 10px 12px; border-bottom: 1px solid #f0f0f0; color: #555; text-align: center; font-size: 14px;">{item_qty}</td>
            <td style="padding: 10px 12px; border-bottom: 1px solid #f0f0f0; color: #333; text-align: right; font-weight: 600; font-size: 14px;">{item_price}</td>
        </tr>
        """

    total_price = f"₹ {order.total_price:.2f}"

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Order Ready for Pickup</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f6f8fa; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: #f6f8fa; padding: 30px 12px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" style="max-width: 560px; background-color: #ffffff; border-radius: 14px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.06);" cellspacing="0" cellpadding="0" border="0">
          
          <!-- Header Banner -->
          <tr>
            <td style="background-color: #AF0C3E; padding: 26px 28px; text-align: center;">
              <h1 style="color: #ffffff; margin: 0; font-size: 22px; font-weight: 700; letter-spacing: -0.2px;">Amrita Canteen</h1>
              <p style="color: rgba(255,255,255,0.85); margin: 6px 0 0; font-size: 13px;">Campus Dining & Meal Service</p>
            </td>
          </tr>

          <!-- Success Pickup Alert -->
          <tr>
            <td style="padding: 28px 28px 12px; text-align: center;">
              <div style="display: inline-block; background-color: #e8f5e9; border: 1.5px solid #2e7d32; border-radius: 30px; padding: 8px 22px; margin-bottom: 14px;">
                <span style="color: #1b5e20; font-weight: 700; font-size: 14px; letter-spacing: 0.3px;">🎉 READY FOR PICKUP</span>
              </div>
              <h2 style="color: #1a202c; margin: 0 0 8px; font-size: 20px; font-weight: 700;">Hello {user_name}!</h2>
              <p style="color: #4a5568; margin: 0; font-size: 15px; line-height: 1.5;">
                Your order is freshly prepared and waiting for you at the counter!
              </p>
            </td>
          </tr>

          <!-- Order & Counter Box -->
          <tr>
            <td style="padding: 12px 28px;">
              <div style="background-color: #fff9db; border: 1.5px dashed #f59f00; border-radius: 10px; padding: 16px; text-align: center;">
                <div style="font-size: 12px; font-weight: 700; color: #856404; text-transform: uppercase; letter-spacing: 0.8px;">Order Number</div>
                <div style="font-size: 30px; font-weight: 800; color: #d9480f; margin: 4px 0;">#{order.id}</div>
                <div style="font-size: 13px; color: #495057;">
                  <strong>Pickup Location:</strong> {canteen_name} ({canteen_location})
                </div>
              </div>
            </td>
          </tr>

          <!-- Items Table -->
          <tr>
            <td style="padding: 16px 28px;">
              <h3 style="color: #2d3748; font-size: 15px; margin: 0 0 10px; border-bottom: 1.5px solid #edf2f7; padding-bottom: 8px;">Order Details</h3>
              <table width="100%" cellspacing="0" cellpadding="0" border="0" style="border-collapse: collapse;">
                <thead>
                  <tr style="background-color: #f8fafc;">
                    <th style="padding: 8px 12px; text-align: left; font-size: 12px; color: #718096; text-transform: uppercase; font-weight: 600;">Item</th>
                    <th style="padding: 8px 12px; text-align: center; font-size: 12px; color: #718096; text-transform: uppercase; font-weight: 600;">Qty</th>
                    <th style="padding: 8px 12px; text-align: right; font-size: 12px; color: #718096; text-transform: uppercase; font-weight: 600;">Price</th>
                  </tr>
                </thead>
                <tbody>
                  {items_rows_html}
                  <tr>
                    <td colspan="2" style="padding: 14px 12px; text-align: right; font-size: 15px; font-weight: 700; color: #1a202c;">Total Paid:</td>
                    <td style="padding: 14px 12px; text-align: right; font-size: 16px; font-weight: 800; color: #AF0C3E;">{total_price}</td>
                  </tr>
                </tbody>
              </table>
            </td>
          </tr>

          <!-- Instructions Card -->
          <tr>
            <td style="padding: 8px 28px 24px;">
              <div style="background-color: #f7fafc; border-radius: 8px; padding: 14px 16px; font-size: 13px; color: #4a5568; line-height: 1.5;">
                💡 <strong>Pickup Tip:</strong> Please show this Order ID (<strong>#{order.id}</strong>) or your Orders page at the counter to collect your food. Enjoy your meal!
              </div>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background-color: #f8f9fa; border-top: 1px solid #edf2f7; padding: 18px 28px; text-align: center;">
              <p style="color: #a0aec0; margin: 0; font-size: 12px;">
                Amrita Vishwa Vidyapeetham • Canteen Management System
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def send_order_ready_email(order_id):
    """
    Sends the 'Ready for Pickup' email for the specified order using Brevo API.
    Executed in a background thread to prevent blocking HTTP endpoints.
    """
    try:
        order = Order.objects.select_related("user", "canteen").prefetch_related("items__product").get(id=order_id)
    except Exception as exc:
        logger.warning(f"[Brevo] Unable to load order #{order_id} for email notification: {exc}")
        return False

    recipient_email = (order.user.email or "").strip()
    if not recipient_email:
        logger.info(f"[Brevo] Order #{order.id}: User '{order.user.username}' has no email in database. Skipping notification.")
        return False

    api_key = getattr(settings, "BREVO_API_KEY", "").strip()
    if not api_key:
        logger.warning(f"[Brevo] BREVO_API_KEY is not configured in settings. Skipping email for Order #{order.id}.")
        return False

    recipient_name = order.user.first_name or order.user.username or "Student"
    sender_email = getattr(settings, "BREVO_SENDER_EMAIL", "hari367854@gmail.com")
    sender_name = getattr(settings, "BREVO_SENDER_NAME", "Amrita Canteen")

    items = list(order.items.all())
    html_content = build_order_ready_html(order, items)
    subject = f"🎉 Your Order #{order.id} is Ready for Pickup! - {order.canteen.name if order.canteen else 'Canteen'}"

    # If key is an SMTP key (starts with 'xsmtpsib-'), send via Brevo SMTP Relay
    if api_key.startswith("xsmtpsib-"):
        from django.core.mail.backends.smtp import EmailBackend
        from django.core.mail import EmailMultiAlternatives

        smtp_server = getattr(settings, "BREVO_SMTP_SERVER", "smtp-relay.brevo.com")
        smtp_port = getattr(settings, "BREVO_SMTP_PORT", 587)
        smtp_login = getattr(settings, "BREVO_SMTP_LOGIN", "ae7576001@smtp-brevo.com")

        try:
            backend = EmailBackend(
                host=smtp_server,
                port=smtp_port,
                username=smtp_login,
                password=api_key,
                use_tls=True,
                timeout=15,
            )
            msg = EmailMultiAlternatives(
                subject=subject,
                body=f"Your order #{order.id} is ready for pickup at {order.canteen.name if order.canteen else 'Canteen'}!",
                from_email=f"{sender_name} <{sender_email}>",
                to=[recipient_email],
                connection=backend,
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send(fail_silently=False)
            logger.info(f"[Brevo SMTP] Successfully sent Order Ready email for Order #{order.id} to {recipient_email}.")
            return True
        except Exception as err:
            logger.error(f"[Brevo SMTP] Error sending email for Order #{order.id}: {err}")
            return False

    # Otherwise, send via Brevo REST API (for 'xkeysib-...' keys)
    payload = {
        "sender": {
            "name": sender_name,
            "email": sender_email,
        },
        "to": [
            {
                "email": recipient_email,
                "name": recipient_name,
            }
        ],
        "subject": subject,
        "htmlContent": html_content,
    }

    req = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "AmritaCanteenSystem/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            resp_body = response.read().decode("utf-8")
            logger.info(f"[Brevo API] Successfully sent Order Ready email for Order #{order.id} to {recipient_email}. Response: {resp_body}")
            return True
    except urllib.error.HTTPError as err:
        err_msg = err.read().decode("utf-8", errors="replace")
        logger.error(f"[Brevo API] HTTP {err.code} while sending email for Order #{order.id}: {err_msg}")
        return False
    except Exception as err:
        logger.error(f"[Brevo API] Error sending email for Order #{order.id}: {err}")
        return False


def send_order_ready_email_async(order):
    """
    Spawns a daemon thread to send the Order Ready email without blocking HTTP responses.
    """
    if not order or not getattr(order, "id", None):
        return

    thread = threading.Thread(
        target=send_order_ready_email,
        args=(order.id,),
        daemon=True,
        name=f"Brevo-OrderReady-{order.id}"
    )
    thread.start()
