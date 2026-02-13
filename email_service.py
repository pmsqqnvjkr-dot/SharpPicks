import os
import logging
import resend

resend.api_key = os.environ.get('RESEND_API_KEY', '')

FROM_EMAIL = "Sharp Picks <info@sharppicks.ai>"

def send_email(to, subject, html):
    if not resend.api_key:
        logging.warning(f"RESEND_API_KEY not set. Email to {to} not sent.")
        return False
    try:
        params = {
            "from": FROM_EMAIL,
            "to": [to],
            "subject": subject,
            "html": html,
        }
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
        <span style="font-size: 14px; font-weight: 700; letter-spacing: 2px; color: #ffffff; text-transform: uppercase;">Sharp Picks</span>
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
    name = first_name or "there"
    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 480px; margin: 0 auto; padding: 40px 20px; color: #e0e0e0; background-color: #0A0D14;">
      <div style="text-align: center; margin-bottom: 32px;">
        <span style="font-size: 14px; font-weight: 700; letter-spacing: 2px; color: #ffffff; text-transform: uppercase;">Sharp Picks</span>
      </div>
      <h2 style="font-size: 20px; font-weight: 600; color: #ffffff; margin-bottom: 8px;">Welcome, {name}</h2>
      <p style="font-size: 15px; line-height: 1.6; color: #a0a0a0;">Your 14-day trial is active. Here's what to expect:</p>
      <div style="background-color: #111420; border-radius: 12px; padding: 20px; margin: 24px 0; border: 1px solid #1a1d28;">
        <p style="font-size: 14px; color: #a0a0a0; margin: 0 0 12px;"><strong style="color: #fff;">One pick per day, maximum.</strong> Most days, you'll see no pick at all. That's the system working.</p>
        <p style="font-size: 14px; color: #a0a0a0; margin: 0 0 12px;"><strong style="color: #fff;">Silence is discipline.</strong> We only publish when the model identifies a genuine statistical edge.</p>
        <p style="font-size: 14px; color: #a0a0a0; margin: 0;"><strong style="color: #fff;">All picks are public.</strong> No deletes. No edits. Full transparency.</p>
      </div>
      <p style="font-size: 13px; color: #666;">Your trial runs for 14 days with full access. No card required.</p>
      <hr style="border: none; border-top: 1px solid #1a1d24; margin: 32px 0;">
      <p style="font-size: 12px; color: #555; text-align: center;">Sharp Picks &mdash; Discipline is the product.</p>
    </div>
    """
    return send_email(to, f"Welcome to Sharp Picks, {name}", html)
