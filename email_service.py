import os
import logging
import resend

resend.api_key = os.environ.get('RESEND_API_KEY', '')

FROM_EMAIL = "Sharp Picks <no-reply@sharppicks.ai>"
ERIN_EMAIL = "Erin Donnelly <erin@sharppicks.ai>"
LOGO_URL = "https://sharppicks.ai/logo-horizontal.png"

def send_email(to, subject, html, reply_to=None, from_email=None):
    if not resend.api_key:
        logging.warning(f"RESEND_API_KEY not set. Email to {to} not sent.")
        return False
    try:
        params = {
            "from": from_email or FROM_EMAIL,
            "to": [to],
            "subject": subject,
            "html": html,
        }
        if reply_to:
            params["reply_to"] = reply_to
        r = resend.Emails.send(params)
        logging.info(f"Email sent to {to}: {r}")
        return True
    except Exception as e:
        logging.error(f"Failed to send email to {to}: {e}")
        return False


def send_password_reset(to, reset_url, first_name=None):
    name = first_name or "there"
    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 480px; margin: 0 auto; padding: 40px 20px; color: #e0e0e0; background-color: #0A0D14;">
      <div style="text-align: center; margin-bottom: 32px;">
        <img src="{LOGO_URL}" alt="Sharp Picks" style="height: 48px; width: auto;" />
      </div>
      <h2 style="font-size: 20px; font-weight: 600; color: #ffffff; margin-bottom: 8px;">Reset your password</h2>
      <p style="font-size: 15px; line-height: 1.6; color: #a0a0a0;">Hi {name}, we received a request to reset your password. Click the button below to choose a new one.</p>
      <div style="text-align: center; margin: 32px 0;">
        <a href="{reset_url}" style="display: inline-block; padding: 14px 32px; background-color: #4F86F7; color: #ffffff; text-decoration: none; border-radius: 10px; font-size: 15px; font-weight: 600;">Reset Password</a>
      </div>
      <p style="font-size: 13px; color: #666;">This link expires in 1 hour. If you didn't request this, you can safely ignore this email.</p>
      <hr style="border: none; border-top: 1px solid #1a1d24; margin: 32px 0;">
      <p style="font-size: 12px; color: #555; text-align: center;">Sharp Picks &mdash; Discipline is the product.</p>
    </div>
    """
    return send_email(to, "Reset your password — Sharp Picks", html)


def send_welcome(to, first_name=None):
    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 520px; margin: 0 auto; padding: 48px 24px; color: #e0e0e0; background-color: #0A0D14;">
      <div style="text-align: center; margin-bottom: 40px;">
        <img src="{LOGO_URL}" alt="Sharp Picks" style="height: 48px; width: auto;" />
      </div>

      <p style="font-size: 15px; line-height: 1.9; color: #b8b8b8; margin-bottom: 24px;">Hi &#8212;</p>

      <p style="font-size: 15px; line-height: 1.9; color: #b8b8b8; margin-bottom: 24px;">I'm Erin, founder of Sharp Picks. I'm glad you're here.</p>

      <p style="font-size: 15px; line-height: 1.9; color: #b8b8b8; margin-bottom: 24px;">Sharp Picks was not built to chase action. It was built to protect capital.</p>

      <p style="font-size: 15px; line-height: 1.9; color: #b8b8b8; margin-bottom: 24px;">Most bettors do not lose because they lack insight. They lose because they treat every edge the same.</p>

      <p style="font-size: 15px; line-height: 1.9; color: #b8b8b8; margin-bottom: 24px;">A small edge on a tight spread is not the same as a small edge on a wide one. The variance is different. The risk is different. The margin for error is different.</p>

      <p style="font-size: 15px; line-height: 1.9; color: #b8b8b8; margin-bottom: 24px;">Most models ignore that.</p>

      <p style="font-size: 15px; line-height: 1.9; color: #ffffff; font-weight: 600; margin-bottom: 24px;">This one does not.</p>

      <p style="font-size: 15px; line-height: 1.9; color: #b8b8b8; margin-bottom: 24px;">Sharp Picks only publishes when a game clears strict confidence and edge thresholds. Most days, that means we pass.</p>

      <div style="margin: 32px 0; padding: 20px 0; border-top: 1px solid #1a1d28; border-bottom: 1px solid #1a1d28;">
        <p style="font-size: 16px; line-height: 1.9; color: #b8b8b8; margin-bottom: 4px;">You will not see ten plays a night.</p>
        <p style="font-size: 16px; line-height: 1.9; color: #ffffff; font-weight: 600; margin: 0;">You will see discipline.</p>
      </div>

      <p style="font-size: 15px; line-height: 1.9; color: #b8b8b8; margin-bottom: 14px;">Every published pick includes:</p>
      <ul style="font-size: 15px; line-height: 2.2; color: #b8b8b8; padding-left: 20px; margin-bottom: 24px;">
        <li>Projected margin</li>
        <li>Cover probability</li>
        <li>Market implied probability</li>
        <li>Calibrated edge</li>
        <li>Clear reasoning behind the signal</li>
      </ul>

      <p style="font-size: 15px; line-height: 1.9; color: #b8b8b8; margin-bottom: 24px;">Everything is tracked. Results are transparent. Nothing is hidden behind marketing language.</p>

      <p style="font-size: 15px; line-height: 1.9; color: #b8b8b8; margin-bottom: 12px;">Sharp Picks is built on one principle:</p>

      <div style="margin: 28px 0 28px 0; padding: 20px 24px; border-left: 3px solid #34D399;">
        <p style="font-size: 17px; line-height: 1.8; color: #34D399; font-weight: 600; font-style: italic; margin: 0;">If risk increases, conviction must increase.</p>
      </div>

      <p style="font-size: 15px; line-height: 1.9; color: #b8b8b8; margin-bottom: 6px;">That is why we pass more than we play.</p>
      <p style="font-size: 15px; line-height: 1.9; color: #b8b8b8; margin-bottom: 24px;">That is why discipline compounds.</p>

      <p style="font-size: 15px; line-height: 1.9; color: #b8b8b8; margin-bottom: 32px;">If you ever want to understand the thinking deeper, just reply to this email. I read every message.</p>

      <p style="font-size: 15px; line-height: 1.9; color: #b8b8b8; margin-bottom: 32px;">Let's stay sharp.</p>

      <p style="font-size: 15px; line-height: 1.6; color: #ffffff; font-weight: 600; margin-bottom: 2px;">Erin Donnelly</p>
      <p style="font-size: 13px; line-height: 1.6; color: #777; margin-bottom: 0;">Founder, Sharp Picks</p>

      <hr style="border: none; border-top: 1px solid #1a1d24; margin: 36px 0;">
      <p style="font-size: 12px; color: #555; text-align: center; letter-spacing: 0.5px;">Sharp Picks</p>
      <p style="font-size: 11px; color: #444; text-align: center; letter-spacing: 0.3px; margin-top: 4px;">Discipline is the product.</p>
    </div>
    """
    return send_email(
        to,
        "Welcome to Sharp Picks",
        html,
        reply_to="erin@sharppicks.ai",
        from_email=ERIN_EMAIL
    )
