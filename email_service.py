import os
import logging
import resend

resend.api_key = os.environ.get('RESEND_API_KEY', '')

FROM_EMAIL = "Sharp Picks <no-reply@sharppicks.ai>"
ERIN_EMAIL = "Erin Donnelly <erin@sharppicks.ai>"

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
    html = """
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 520px; margin: 0 auto; padding: 40px 20px; color: #e0e0e0; background-color: #0A0D14;">
      <div style="text-align: center; margin-bottom: 32px;">
        <span style="font-size: 14px; font-weight: 700; letter-spacing: 2px; color: #ffffff; text-transform: uppercase;">Sharp Picks</span>
      </div>

      <p style="font-size: 15px; line-height: 1.8; color: #c0c0c0; margin-bottom: 20px;">Hi &mdash;</p>

      <p style="font-size: 15px; line-height: 1.8; color: #c0c0c0; margin-bottom: 20px;">I'm Erin, founder of Sharp Picks. I'm glad you're here.</p>

      <p style="font-size: 15px; line-height: 1.8; color: #c0c0c0; margin-bottom: 20px;">This is not a picks service built on volume. Most days, we pass. When the model publishes, it's because a game cleared strict confidence and edge thresholds.</p>

      <p style="font-size: 15px; line-height: 1.8; color: #c0c0c0; margin-bottom: 4px;">You won't see ten plays a night.</p>
      <p style="font-size: 15px; line-height: 1.8; color: #ffffff; font-weight: 600; margin-bottom: 20px;">You'll see discipline.</p>

      <p style="font-size: 15px; line-height: 1.8; color: #c0c0c0; margin-bottom: 12px;">Every published pick includes:</p>
      <ul style="font-size: 15px; line-height: 2.0; color: #c0c0c0; padding-left: 20px; margin-bottom: 20px;">
        <li>Projected margin</li>
        <li>Cover probability</li>
        <li>Market implied probability</li>
        <li>Calibrated edge</li>
        <li>Clear reasoning behind the signal</li>
      </ul>

      <p style="font-size: 15px; line-height: 1.8; color: #c0c0c0; margin-bottom: 20px;">Everything is standardized. Everything is tracked. Nothing is hidden.</p>

      <p style="font-size: 15px; line-height: 1.8; color: #c0c0c0; margin-bottom: 20px;">If you ever have questions, feedback, or just want to understand the thinking deeper, reply directly to this email. I read them all.</p>

      <p style="font-size: 15px; line-height: 1.8; color: #c0c0c0; margin-bottom: 8px;">Sharp Picks is built on one idea:</p>

      <p style="font-size: 16px; line-height: 1.8; color: #ffffff; font-weight: 600; font-style: italic; margin-bottom: 24px;">If risk increases, conviction must increase.</p>

      <p style="font-size: 15px; line-height: 1.8; color: #c0c0c0; margin-bottom: 28px;">Let's stay sharp.</p>

      <p style="font-size: 15px; line-height: 1.6; color: #ffffff; margin-bottom: 2px;">Erin Donnelly</p>
      <p style="font-size: 13px; line-height: 1.6; color: #888; margin-bottom: 0;">Founder, Sharp Picks</p>

      <hr style="border: none; border-top: 1px solid #1a1d24; margin: 32px 0;">
      <p style="font-size: 12px; color: #555; text-align: center;">Sharp Picks &mdash; Discipline is the product.</p>
    </div>
    """
    return send_email(
        to,
        "Welcome to Sharp Picks",
        html,
        reply_to="erin@sharppicks.ai",
        from_email=ERIN_EMAIL
    )
