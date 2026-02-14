import os
import logging
import resend

resend.api_key = os.environ.get('RESEND_API_KEY', '')

FROM_EMAIL = "Sharp Picks <no-reply@sharppicks.ai>"
FOUNDER_EMAIL = "Evan Cole <evan@sharppicks.ai>"

def get_base_url():
    domain = os.environ.get('REPLIT_DOMAINS', os.environ.get('REPLIT_DEV_DOMAIN', ''))
    if domain:
        domain = domain.split(',')[0].strip()
        return f"https://{domain}"
    return "https://sharppicks.ai"

def get_logo_url():
    return f"{get_base_url()}/logo-email.png"

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
        <img src="{get_logo_url()}" alt="Sharp Picks" style="height: 120px; width: auto;" />
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
    dashboard_url = get_logo_url().rsplit('/', 1)[0]
    html = f"""
    <div style="font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 520px; margin: 0 auto; padding: 48px 24px; color: #e0e0e0; background-color: #0A0D14;">
      <div style="text-align: center; margin-bottom: 40px;">
        <img src="{get_logo_url()}" alt="Sharp Picks" style="height: 120px; width: auto;" />
      </div>

      <p style="font-size: 15px; line-height: 1.9; color: #b8b8b8; margin-bottom: 24px;">Hi {name},</p>

      <p style="font-size: 15px; line-height: 1.9; color: #b8b8b8; margin-bottom: 24px;">Welcome to Sharp Picks.</p>

      <p style="font-size: 15px; line-height: 1.9; color: #b8b8b8; margin-bottom: 24px;">Most people treat sports betting like a game of luck. We treat it like a market. By joining this community, you've chosen to move away from the noise and toward a data-driven, disciplined approach.</p>

      <p style="font-size: 15px; line-height: 1.9; color: #b8b8b8; margin-bottom: 24px;">Evan Cole here. I built this platform because I was tired of the "hype" culture. I wanted a tool that prioritized institutional-grade tracking and transparency over flashy promos.</p>

      <p style="font-size: 15px; line-height: 1.9; color: #ffffff; font-weight: 600; margin-bottom: 16px;">Here is how to get the most out of your first 24 hours:</p>

      <table style="width: 100%; border-collapse: collapse; margin-bottom: 28px;">
        <tr>
          <td style="padding: 14px 16px; border-bottom: 1px solid #1a1d28;">
            <span style="font-size: 14px; font-weight: 700; color: #34D399; margin-right: 10px;">1.</span>
            <span style="font-size: 15px; color: #ffffff; font-weight: 600;">Set Your Unit Size</span>
            <p style="font-size: 13px; color: #888; margin: 4px 0 0 22px; line-height: 1.6;">Discipline starts with bankroll management.</p>
          </td>
        </tr>
        <tr>
          <td style="padding: 14px 16px; border-bottom: 1px solid #1a1d28;">
            <span style="font-size: 14px; font-weight: 700; color: #34D399; margin-right: 10px;">2.</span>
            <span style="font-size: 15px; color: #ffffff; font-weight: 600;">Explore Today's Analysis</span>
            <p style="font-size: 13px; color: #888; margin: 4px 0 0 22px; line-height: 1.6;">See what the model found &#8212; or why it passed.</p>
          </td>
        </tr>
        <tr>
          <td style="padding: 14px 16px;">
            <span style="font-size: 14px; font-weight: 700; color: #34D399; margin-right: 10px;">3.</span>
            <span style="font-size: 15px; color: #ffffff; font-weight: 600;">Review the Public Record</span>
            <p style="font-size: 13px; color: #888; margin: 4px 0 0 22px; line-height: 1.6;">Every pick and pass tracked transparently &#8212; verified by data, not talk.</p>
          </td>
        </tr>
      </table>

      <div style="margin: 28px 0 28px 0; padding: 20px 24px; border-left: 3px solid #34D399;">
        <p style="font-size: 17px; line-height: 1.8; color: #34D399; font-weight: 600; font-style: italic; margin: 0;">The goal isn't just to win a bet; it's to build a sustainable edge.</p>
      </div>

      <div style="text-align: center; margin: 32px 0;">
        <a href="{dashboard_url}" style="display: inline-block; padding: 14px 36px; background-color: #4F86F7; color: #ffffff; text-decoration: none; border-radius: 10px; font-size: 15px; font-weight: 600; font-family: 'Inter', sans-serif; letter-spacing: 0.3px;">ACCESS YOUR DASHBOARD</a>
      </div>

      <p style="font-size: 15px; line-height: 1.9; color: #b8b8b8; margin-bottom: 32px;">If you have questions or feedback on the interface, reply directly to this email. I'm personally looking for ways to make our tools sharper for you.</p>

      <p style="font-size: 15px; line-height: 1.9; color: #b8b8b8; margin-bottom: 32px;">To the edge,</p>

      <div style="margin-bottom: 8px;">
        <img src="{get_base_url()}/evan-signature.png" alt="Evan" style="height: 52px; width: auto; display: block;" />
      </div>
      <div style="display: flex; align-items: center; gap: 8px;">
        <div style="width: 28px; height: 28px; border-radius: 50%; background-color: #1a1d28; border: 1px solid #2a2d38; display: inline-block; vertical-align: middle; text-align: center; line-height: 26px;">
          <span style="font-size: 12px; color: #888;">EC</span>
        </div>
        <span style="font-size: 14px; color: #ffffff; font-weight: 600; font-family: 'Inter', -apple-system, sans-serif; vertical-align: middle;">Evan Cole</span>
      </div>
      <p style="font-size: 13px; line-height: 1.6; color: #777; margin: 4px 0 0 36px;">Founder, Sharp Picks</p>

      <hr style="border: none; border-top: 1px solid #1a1d24; margin: 36px 0;">
      <div style="text-align: center; margin-bottom: 16px;">
        <a href="https://x.com/sharppicks" style="display: inline-block; margin: 0 8px; text-decoration: none;">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="#555" xmlns="http://www.w3.org/2000/svg"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
        </a>
        <a href="https://instagram.com/sharppicks" style="display: inline-block; margin: 0 8px; text-decoration: none;">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="#555" xmlns="http://www.w3.org/2000/svg"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z"/></svg>
        </a>
      </div>
      <p style="font-size: 12px; color: #555; text-align: center; letter-spacing: 0.5px;">Sharp Picks</p>
      <p style="font-size: 11px; color: #444; text-align: center; letter-spacing: 0.3px; margin-top: 4px;">Discipline is the edge.</p>
    </div>
    """
    return send_email(
        to,
        "Welcome to Sharp Picks | The Edge is Discipline",
        html,
        reply_to="evan@sharppicks.ai",
        from_email=FOUNDER_EMAIL
    )
