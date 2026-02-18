import os
import base64
import logging
import resend

resend.api_key = os.environ.get('RESEND_API_KEY', '')

FROM_EMAIL = "Sharp Picks <info@sharppicks.ai>"
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


def send_verification_email(to, verify_url, first_name=None):
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
      <h2 style="font-size: 20px; font-weight: 600; color: #ffffff; margin-bottom: 8px;">Verify your email</h2>
      <p style="font-size: 15px; line-height: 1.6; color: #a0a0a0;">Hi {name}, thanks for signing up for Sharp Picks. Please verify your email to activate your account.</p>
      <div style="text-align: center; margin: 32px 0;">
        <a href="{verify_url}" style="display: inline-block; padding: 14px 32px; background-color: #4F86F7; color: #ffffff; text-decoration: none; border-radius: 10px; font-size: 15px; font-weight: 600;">Verify Email Address</a>
      </div>
      <p style="font-size: 13px; color: #666;">This link expires in 24 hours. If you didn't create this account, you can safely ignore this email.</p>
      <hr style="border: none; border-top: 1px solid #1a1d24; margin: 32px 0;">
      <p style="font-size: 12px; color: #555; text-align: center;">Sharp Picks &mdash; Discipline is the product.</p>
    </div>
    """
    return send_email(to, "Verify your email — Sharp Picks", html, attachments=attachments or None)


def send_welcome_email(to, first_name=None):
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
    upgrade_url = f"{get_base_url()}/"

    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 480px; margin: 0 auto; padding: 40px 20px; color: #e0e0e0; background-color: #0A0D14;">
      <div style="text-align: center; margin-bottom: 32px;">
        <img src="{logo_src}" alt="Sharp Picks" style="height: 120px; width: auto;" />
      </div>
      <h2 style="font-size: 20px; font-weight: 600; color: #ffffff; margin-bottom: 8px;">Welcome to Sharp Picks</h2>
      <p style="font-size: 15px; line-height: 1.6; color: #a0a0a0;">Hi {name}, your free account is ready.</p>
      <p style="font-size: 15px; line-height: 1.6; color: #a0a0a0;">With your free account you can follow the model's daily activity, view the public record, and read pass-day summaries. When you're ready for full pick details, edge percentages, and bet tracking, upgrade to Pro with a 14-day free trial.</p>
      <div style="text-align: center; margin: 32px 0;">
        <a href="{upgrade_url}" style="display: inline-block; padding: 14px 32px; background-color: #4F86F7; color: #ffffff; text-decoration: none; border-radius: 10px; font-size: 15px; font-weight: 600;">Open Sharp Picks</a>
      </div>
      <hr style="border: none; border-top: 1px solid #1a1d24; margin: 32px 0;">
      <p style="font-size: 12px; color: #555; text-align: center;">Sharp Picks &mdash; Discipline is the product.</p>
    </div>
    """
    return send_email(to, "Welcome to Sharp Picks", html, attachments=attachments or None)


def send_trial_expiring_email(to, first_name=None, trial_end_date=None, picks_record=None, founding_spots=None):
    name = first_name or "there"
    end_str = trial_end_date.strftime('%B %d, %Y') if trial_end_date else "soon"
    record_str = picks_record or "Check your dashboard for details"
    founding_line = f"Founding rate: $99/year ({founding_spots} of 50 spots remaining)" if founding_spots else "Founding rate: $99/year (limited spots)"

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
    subscribe_url = f"{get_base_url()}/subscribe"

    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 480px; margin: 0 auto; padding: 40px 20px; color: #e0e0e0; background-color: #0A0D14;">
      <div style="text-align: center; margin-bottom: 32px;">
        <img src="{logo_src}" alt="Sharp Picks" style="height: 120px; width: auto;" />
      </div>
      <h2 style="font-size: 20px; font-weight: 600; color: #ffffff; margin-bottom: 8px;">Your trial ends in 2 days</h2>
      <p style="font-size: 15px; line-height: 1.6; color: #a0a0a0;">Hi {name}, your 14-day Sharp Picks trial ends on {end_str}.</p>
      <p style="font-size: 15px; line-height: 1.6; color: #a0a0a0;">During your trial: {record_str}</p>
      <p style="font-size: 15px; line-height: 1.6; color: #a0a0a0;">Subscribe to keep full access:</p>
      <div style="padding: 16px; background-color: rgba(79,134,247,0.08); border-radius: 10px; margin: 16px 0;">
        <p style="font-size: 14px; color: #a0a0a0; margin: 4px 0;">&rarr; {founding_line}</p>
        <p style="font-size: 14px; color: #a0a0a0; margin: 4px 0;">&rarr; Monthly: $29/month</p>
      </div>
      <div style="text-align: center; margin: 32px 0;">
        <a href="{subscribe_url}" style="display: inline-block; padding: 14px 32px; background-color: #4F86F7; color: #ffffff; text-decoration: none; border-radius: 10px; font-size: 15px; font-weight: 600;">Subscribe Now</a>
      </div>
      <hr style="border: none; border-top: 1px solid #1a1d24; margin: 32px 0;">
      <p style="font-size: 12px; color: #555; text-align: center;">Sharp Picks &mdash; Discipline is the product.</p>
    </div>
    """
    return send_email(to, "Your trial ends in 2 days — Sharp Picks", html, attachments=attachments or None)


def send_trial_expired_email(to, first_name=None):
    name = first_name or "there"
    subscribe_url = f"{get_base_url()}/subscribe"

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
      <h2 style="font-size: 20px; font-weight: 600; color: #ffffff; margin-bottom: 8px;">Your trial has ended</h2>
      <p style="font-size: 15px; line-height: 1.6; color: #a0a0a0;">Hi {name}, your Sharp Picks trial has expired. You've been moved to the free tier with limited access.</p>
      <p style="font-size: 15px; line-height: 1.6; color: #a0a0a0;">Subscribe to restore full access to every qualified pick, edge analysis, and performance tracking.</p>
      <div style="text-align: center; margin: 32px 0;">
        <a href="{subscribe_url}" style="display: inline-block; padding: 14px 32px; background-color: #4F86F7; color: #ffffff; text-decoration: none; border-radius: 10px; font-size: 15px; font-weight: 600;">Subscribe Now</a>
      </div>
      <hr style="border: none; border-top: 1px solid #1a1d24; margin: 32px 0;">
      <p style="font-size: 12px; color: #555; text-align: center;">Sharp Picks &mdash; Discipline is the product.</p>
    </div>
    """
    return send_email(to, "Your trial has ended — Sharp Picks", html, attachments=attachments or None)


def send_cancellation_email(to, first_name=None, access_end_date=None, is_founding=False):
    name = first_name or "there"
    end_str = access_end_date.strftime('%B %d, %Y') if access_end_date else "the end of your billing period"
    resubscribe_url = f"{get_base_url()}/subscribe"

    founding_warning = ""
    if is_founding:
        founding_warning = """
        <div style="padding: 16px; background-color: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.15); border-radius: 10px; margin: 16px 0;">
          <p style="font-size: 14px; color: #f87171; margin: 0; font-weight: 600;">Your founding member rate ($99/year) cannot be restored if you resubscribe later.</p>
        </div>
        """

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
      <h2 style="font-size: 20px; font-weight: 600; color: #ffffff; margin-bottom: 8px;">Your subscription has been cancelled</h2>
      <p style="font-size: 15px; line-height: 1.6; color: #a0a0a0;">Hi {name}, your subscription has been cancelled. You'll continue to have full access through {end_str}.</p>
      <p style="font-size: 15px; line-height: 1.6; color: #a0a0a0;">After that date, you'll move to the free tier with limited access to model output.</p>
      {founding_warning}
      <p style="font-size: 15px; line-height: 1.6; color: #a0a0a0;">If this was a mistake, you can resubscribe anytime before your access expires.</p>
      <div style="text-align: center; margin: 32px 0;">
        <a href="{resubscribe_url}" style="display: inline-block; padding: 14px 32px; background-color: #4F86F7; color: #ffffff; text-decoration: none; border-radius: 10px; font-size: 15px; font-weight: 600;">Resubscribe</a>
      </div>
      <hr style="border: none; border-top: 1px solid #1a1d24; margin: 32px 0;">
      <p style="font-size: 12px; color: #555; text-align: center;">Sharp Picks &mdash; Discipline is the product.</p>
    </div>
    """
    return send_email(to, "Your Sharp Picks subscription", html, attachments=attachments or None)


def send_payment_failed_email(to, first_name=None):
    name = first_name or "there"
    profile_url = f"{get_base_url()}"

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
      <h2 style="font-size: 20px; font-weight: 600; color: #ffffff; margin-bottom: 8px;">Payment issue with your subscription</h2>
      <p style="font-size: 15px; line-height: 1.6; color: #a0a0a0;">Hi {name}, we weren't able to process your latest payment. Stripe will retry automatically, but please update your payment method to avoid any interruption.</p>
      <div style="text-align: center; margin: 32px 0;">
        <a href="{profile_url}" style="display: inline-block; padding: 14px 32px; background-color: #4F86F7; color: #ffffff; text-decoration: none; border-radius: 10px; font-size: 15px; font-weight: 600;">Update Payment Method</a>
      </div>
      <hr style="border: none; border-top: 1px solid #1a1d24; margin: 32px 0;">
      <p style="font-size: 12px; color: #555; text-align: center;">Sharp Picks &mdash; Discipline is the product.</p>
    </div>
    """
    return send_email(to, "Payment issue — Sharp Picks", html, attachments=attachments or None)


def send_weekly_summary(to, first_name=None, stats=None):
    name = first_name or "there"
    s = stats or {}
    picks_made = s.get('picks_made', 0)
    passes = s.get('passes', 0)
    wins = s.get('wins', 0)
    losses = s.get('losses', 0)
    pending = s.get('pending', 0)
    record_str = f"{wins}W-{losses}L" + (f" ({pending} pending)" if pending else "")
    total_record = s.get('total_record', '')
    next_week_games = s.get('next_week_games', 'Full slate')

    base_url = get_base_url()
    dashboard_url = f"{base_url}/"

    attachments = []
    logo_b64 = _get_logo_b64()
    if logo_b64:
        attachments.append({
            "content": logo_b64,
            "filename": "logo.png",
            "content_id": "sp-logo",
            "content_type": "image/png",
        })
    logo_src = 'cid:sp-logo' if logo_b64 else f"{base_url}/logo-email.png"

    html = f"""
    <div style="max-width: 600px; margin: 0 auto; background-color: #0A0D14; padding: 40px 32px; font-family: 'Inter', -apple-system, sans-serif; color: #e0e0e0;">
      <div style="text-align: center; margin-bottom: 32px;">
        <img src="{logo_src}" alt="Sharp Picks" style="height: 80px; width: auto;" />
      </div>

      <div style="font-family: 'Courier New', monospace; font-size: 9px; font-weight: 700; letter-spacing: 2.5px; text-transform: uppercase; color: #4F86F7; margin-bottom: 20px;">Weekly Summary</div>

      <p style="font-size: 16px; line-height: 1.7; color: #b8b8b8; margin-bottom: 24px;">Hey {name}, here's your week in review.</p>

      <div style="background: rgba(79,134,247,0.06); border: 1px solid rgba(79,134,247,0.15); border-radius: 12px; padding: 24px; margin-bottom: 24px;">
        <table style="width: 100%; border-collapse: collapse;">
          <tr>
            <td style="padding: 8px 0;">
              <span style="font-size: 13px; color: #888; text-transform: uppercase; letter-spacing: 1px;">Picks Published</span><br/>
              <span style="font-size: 28px; font-weight: 700; color: #ffffff; font-family: 'JetBrains Mono', monospace;">{picks_made}</span>
            </td>
            <td style="padding: 8px 0;">
              <span style="font-size: 13px; color: #888; text-transform: uppercase; letter-spacing: 1px;">Pass Days</span><br/>
              <span style="font-size: 28px; font-weight: 700; color: #ffffff; font-family: 'JetBrains Mono', monospace;">{passes}</span>
            </td>
            <td style="padding: 8px 0;">
              <span style="font-size: 13px; color: #888; text-transform: uppercase; letter-spacing: 1px;">Week Record</span><br/>
              <span style="font-size: 28px; font-weight: 700; color: {'#34D399' if wins > losses else '#F87171' if losses > wins else '#ffffff'}; font-family: 'JetBrains Mono', monospace;">{record_str}</span>
            </td>
          </tr>
        </table>
      </div>

      {'<p style="font-size: 14px; color: #888; margin-bottom: 16px;">Season record: <span style="color: #ffffff; font-weight: 600;">' + total_record + '</span></p>' if total_record else ''}

      <div style="margin: 24px 0; padding: 16px 20px; border-left: 3px solid #34D399; background-color: rgba(52, 211, 153, 0.04);">
        <div style="font-family: 'Courier New', monospace; font-size: 9px; font-weight: 700; letter-spacing: 2.5px; text-transform: uppercase; color: #34D399; margin-bottom: 8px;">This Week&rsquo;s Edge</div>
        <p style="font-family: Georgia, serif; font-size: 16px; line-height: 1.5; color: #ffffff; font-style: italic; margin: 0;">Pass days aren't missed opportunities — they're proof the system is working. Discipline over volume.</p>
      </div>

      <p style="font-size: 14px; color: #888; margin-bottom: 24px;">Next week: {next_week_games}</p>

      <div style="text-align: center; margin: 28px 0;">
        <a href="{dashboard_url}" style="display: inline-block; padding: 14px 36px; background-color: #4F86F7; color: #ffffff; text-decoration: none; border-radius: 10px; font-size: 15px; font-weight: 600;">VIEW DASHBOARD</a>
      </div>

      <hr style="border: none; border-top: 1px solid #1a1d24; margin: 32px 0;">
      <p style="font-size: 12px; color: #555; text-align: center;">Sharp Picks — Discipline is the edge.</p>
      <p style="font-size: 11px; color: #444; text-align: center; margin-top: 4px;">This is entertainment only. Past results don't guarantee future performance.</p>
    </div>
    """
    return send_email(
        to,
        f"Weekly Summary | {record_str}" if picks_made > 0 else "Weekly Summary | All Pass Week",
        html,
        reply_to="evan@sharppicks.ai",
        from_email=FOUNDER_EMAIL,
        attachments=attachments or None,
    )


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
        <a href="https://x.com/SharpPicksApp" style="display: inline-block; margin: 0 8px; text-decoration: none;">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="#555" xmlns="http://www.w3.org/2000/svg"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
        </a>
        <a href="https://instagram.com/SharpPicksOfficial" style="display: inline-block; margin: 0 8px; text-decoration: none;">
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
