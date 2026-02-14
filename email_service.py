import os
import base64
import logging
import resend

resend.api_key = os.environ.get('RESEND_API_KEY', '')

FROM_EMAIL = "Sharp Picks <no-reply@sharppicks.ai>"
FOUNDER_EMAIL = "Evan Cole <evan@sharppicks.ai>"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def get_base_url():
    custom = os.environ.get('APP_BASE_URL', '')
    if custom:
        return custom.rstrip('/')
    if os.environ.get('REPLIT_DEPLOYMENT') == '1':
        domain = os.environ.get('REPLIT_DOMAINS', '')
        if domain:
            return f"https://{domain.split(',')[0].strip()}"
    return "https://sharp-picks-erindonnelly4.replit.app"

def _load_image_b64(filename):
    for d in [os.path.join(SCRIPT_DIR, 'public'), os.path.join(SCRIPT_DIR, 'dist')]:
        path = os.path.join(d, filename)
        if os.path.exists(path):
            with open(path, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')
    return None

_logo_b64 = None
_sig_b64 = None

def _get_logo_b64():
    global _logo_b64
    if _logo_b64 is None:
        _logo_b64 = _load_image_b64('logo-email.png')
    return _logo_b64

def _get_sig_b64():
    global _sig_b64
    if _sig_b64 is None:
        _sig_b64 = _load_image_b64('evan-signature.png')
    return _sig_b64

def send_email(to, subject, html, reply_to=None, from_email=None, attachments=None):
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
        if attachments:
            params["attachments"] = attachments
        r = resend.Emails.send(params)
        logging.info(f"Email sent to {to}: {r}")
        return True
    except Exception as e:
        logging.error(f"Failed to send email to {to}: {e}")
        return False


def send_password_reset(to, reset_url, first_name=None):
    name = first_name or "there"

    attachments = []
    logo_b64 = _get_logo_b64()
    if logo_b64:
        attachments.append({
            "content": logo_b64,
            "filename": "logo.png",
            "content_id": "sp-logo",
            "content_type": "image/png",
        })

    logo_src = 'cid:sp-logo' if logo_b64 else f'{get_base_url()}/logo-email.png'

    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 480px; margin: 0 auto; padding: 40px 20px; color: #e0e0e0; background-color: #0A0D14;">
      <div style="text-align: center; margin-bottom: 32px;">
        <img src="{logo_src}" alt="Sharp Picks" style="height: 120px; width: auto;" />
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
    return send_email(to, "Reset your password — Sharp Picks", html, attachments=attachments or None)


def send_welcome(to, first_name=None):
    name = first_name or "there"
    dashboard_url = get_base_url()

    attachments = []
    logo_b64 = _get_logo_b64()
    sig_b64 = _get_sig_b64()

    if logo_b64:
        attachments.append({
            "content": logo_b64,
            "filename": "logo.png",
            "content_id": "sp-logo",
            "content_type": "image/png",
        })
    if sig_b64:
        attachments.append({
            "content": sig_b64,
            "filename": "evan-signature.png",
            "content_id": "evan-sig",
            "content_type": "image/png",
        })

    logo_src = 'cid:sp-logo' if logo_b64 else f'{get_base_url()}/logo-email.png'
    sig_src = 'cid:evan-sig' if sig_b64 else f'{get_base_url()}/evan-signature.png'

    html = f"""
    <div style="font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 520px; margin: 0 auto; padding: 20px 24px 48px; color: #e0e0e0; background-color: #0A0D14;">
      <div style="text-align: center; margin-bottom: 16px;">
        <img src="{logo_src}" alt="Sharp Picks" style="height: 160px; width: auto;" />
      </div>

      <p style="font-size: 15px; line-height: 1.9; color: #b8b8b8; margin-bottom: 24px; margin-top: 0;">Hi {name},</p>

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

      <div style="margin: 28px 0 28px 0; padding: 20px 24px; border-left: 3px solid #34D399; background-color: rgba(52, 211, 153, 0.04);">
        <div style="font-family: 'Courier New', monospace; font-size: 9px; font-weight: 700; letter-spacing: 2.5px; text-transform: uppercase; color: #34D399; margin-bottom: 14px;">Sharp Principle</div>
        <p style="font-family: Georgia, 'Times New Roman', serif; font-size: 19px; line-height: 1.55; color: #ffffff; font-weight: 500; font-style: italic; margin: 0;">The goal isn't just to win a bet; it's to build a sustainable edge.</p>
      </div>

      <div style="text-align: center; margin: 32px 0;">
        <a href="{dashboard_url}" style="display: inline-block; padding: 14px 36px; background-color: #4F86F7; color: #ffffff; text-decoration: none; border-radius: 10px; font-size: 15px; font-weight: 600; font-family: 'Inter', sans-serif; letter-spacing: 0.3px;">ACCESS YOUR DASHBOARD</a>
      </div>

      <p style="font-size: 15px; line-height: 1.9; color: #b8b8b8; margin-bottom: 32px;">If you have questions or feedback on the interface, reply directly to this email. I'm personally looking for ways to make our tools sharper for you.</p>

      <p style="font-size: 15px; line-height: 1.9; color: #b8b8b8; margin-bottom: 4px;">To the edge,</p>

      <div style="margin-bottom: 0; padding-bottom: 0;">
        <img src="{sig_src}" alt="Evan" style="height: 140px; width: auto; display: block; margin-left: -20px; margin-bottom: 0;" />
      </div>
      <table cellpadding="0" cellspacing="0" border="0"><tr>
        <td style="vertical-align: middle; padding-right: 12px;">
          <div style="width: 40px; height: 40px; border-radius: 50%; background: linear-gradient(135deg, rgba(79,134,247,0.2), rgba(52,211,153,0.15)); border: 1px solid rgba(79,134,247,0.3); text-align: center; line-height: 38px;">
            <span style="font-size: 15px; font-weight: 600; color: #4F86F7;">EC</span>
          </div>
        </td>
        <td style="vertical-align: middle;">
          <div style="font-size: 17px; color: #ffffff; font-weight: 600; font-family: 'Inter', -apple-system, sans-serif;">Evan Cole</div>
          <div style="font-size: 13px; color: #777; font-family: 'Inter', -apple-system, sans-serif; margin-top: 2px;">Founder, Sharp Picks</div>
        </td>
      </tr></table>

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
        from_email=FOUNDER_EMAIL,
        attachments=attachments or None,
    )
