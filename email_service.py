import os
import base64
import logging
import resend
from jinja2 import Environment, FileSystemLoader, select_autoescape

resend.api_key = os.environ.get('RESEND_API_KEY', '')

FROM_EMAIL = "SharpPicks <info@sharppicks.ai>"
FOUNDER_EMAIL = "Evan Cole <evan@sharppicks.ai>"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

_jinja_env = Environment(
    loader=FileSystemLoader(os.path.join(SCRIPT_DIR, 'templates', 'emails')),
    autoescape=select_autoescape(['html']),
)

def get_base_url():
    custom = os.environ.get('APP_BASE_URL', '')
    if custom:
        return custom.rstrip('/')
    if os.environ.get('REPLIT_DEPLOYMENT') == '1':
        domain = os.environ.get('REPLIT_DOMAINS', '')
        if domain:
            return f"https://{domain.split(',')[0].strip()}"
    if os.environ.get('RAILWAY_PUBLIC_DOMAIN'):
        return f"https://{os.environ['RAILWAY_PUBLIC_DOMAIN']}"
    return "https://app.sharppicks.ai"

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


def check_email_pref(to_email, pref_key):
    """Check if a user has opted into a specific email category."""
    try:
        from models import User
        user = User.query.filter_by(email=to_email).first()
        if not user:
            return True
        prefs = user.notification_prefs or {}
        return prefs.get(pref_key, True)
    except Exception:
        return True


def _make_unsub_url(to_email, category='all'):
    try:
        from itsdangerous import URLSafeTimedSerializer
        secret = os.environ.get('SESSION_SECRET', os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production'))
        s = URLSafeTimedSerializer(secret)
        token = s.dumps(to_email, salt='email-unsubscribe')
        return f'{get_base_url()}/unsubscribe?token={token}&cat={category}'
    except Exception:
        return f'{get_base_url()}/unsubscribe'


def _render(template_name, props):
    """Render a React Email template, falling back to None on error."""
    try:
        from email_renderer import render_template
        return render_template(template_name, props)
    except Exception as e:
        logging.warning(f"React Email render failed for '{template_name}', will use legacy: {e}")
        return None


def _render_jinja(template_name, context):
    """Render a Jinja2 email template from templates/emails/."""
    try:
        tpl = _jinja_env.get_template(template_name)
        return tpl.render(**context)
    except Exception as e:
        logging.warning(f"Jinja2 render failed for '{template_name}': {e}")
        return None


def _get_shared_email_context():
    """Build shared template variables: season record, last 10 picks."""
    ctx = {}
    try:
        from models import Pick
        settled = Pick.query.filter(
            Pick.result.in_(['win', 'loss'])
        ).all()
        ctx['season_record_wins'] = sum(1 for p in settled if p.result == 'win')
        ctx['season_record_losses'] = sum(1 for p in settled if p.result == 'loss')

        clv_vals = [p.clv for p in settled if p.clv is not None]
        clv_pos = sum(1 for v in clv_vals if v > 0)
        ctx['season_clv'] = round(clv_pos / len(clv_vals) * 100, 1) if clv_vals else 0

        recent = Pick.query.filter(
            Pick.result.in_(['win', 'loss'])
        ).order_by(Pick.game_date.desc()).limit(10).all()
        ctx['last_10_picks'] = [
            {'result': 'W' if p.result == 'win' else 'L'} for p in reversed(recent)
        ]
    except Exception as e:
        logging.warning(f"Failed to load shared email context: {e}")
        ctx.setdefault('season_record_wins', 0)
        ctx.setdefault('season_record_losses', 0)
        ctx.setdefault('season_clv', 0)
        ctx.setdefault('last_10_picks', [])
    return ctx


# ── Legacy base template (kept as fallback) ──

def _brand_header_html():
    """Inline brand header: SHARP || PICKS — email-safe table-based layout."""
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="display:inline-table;vertical-align:middle;">'
        '<tr>'
        '<td style="font-family:\'SF Mono\',\'Menlo\',\'Consolas\',\'Courier New\',monospace;font-size:13px;font-weight:500;'
        'letter-spacing:0.2em;color:#E8EAED;line-height:1;white-space:nowrap;vertical-align:middle;">SHARP</td>'
        '<td style="vertical-align:middle;padding:0 4px;">'
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:0 auto;">'
        '<tr>'
        '<td style="width:2px;height:14px;background-color:#E8EAED;font-size:0;line-height:0;">&nbsp;</td>'
        '<td style="width:2px;">&nbsp;</td>'
        '<td style="width:2px;height:14px;background-color:#E8EAED;font-size:0;line-height:0;">&nbsp;</td>'
        '</tr>'
        '<tr>'
        '<td colspan="3" style="padding-top:2px;">'
        '<div style="width:100%;height:2px;background-color:#5A9E72;font-size:0;line-height:0;">&nbsp;</div>'
        '</td>'
        '</tr>'
        '</table>'
        '</td>'
        '<td style="font-family:\'SF Mono\',\'Menlo\',\'Consolas\',\'Courier New\',monospace;font-size:13px;font-weight:500;'
        'letter-spacing:0.2em;color:#E8EAED;line-height:1;white-space:nowrap;vertical-align:middle;">PICKS</td>'
        '</tr>'
        '</table>'
    )


def _base_template(type_label, body_html, cta_text=None, cta_url=None,
                   fine_print=None, to_email=None, unsub_category='all',
                   show_store_badge=False):
    base = get_base_url()
    unsub_url = _make_unsub_url(to_email, unsub_category) if to_email else f'{base}/unsubscribe'

    from datetime import datetime
    from zoneinfo import ZoneInfo
    date_str = datetime.now(ZoneInfo('America/New_York')).strftime('%b %d, %Y').upper()

    cta_html = ''
    if cta_text and cta_url:
        cta_html = f'''
        <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:24px 0 0;">
          <tr>
            <td align="center">
              <a href="{cta_url}" style="display:block;width:100%;padding:16px 0;background-color:#5A9E72;color:#E8EAED;text-align:center;text-decoration:none;border-radius:6px;font-family:'SF Pro Display','Helvetica Neue','Arial',sans-serif;font-size:13px;font-weight:600;letter-spacing:0.08em;">{cta_text}</a>
            </td>
          </tr>
        </table>'''

    fine_html = ''
    if fine_print:
        fine_html = f'''
        <p style="font-family:'SF Pro Display','Helvetica Neue','Arial',sans-serif;font-size:12px;color:rgba(232,234,237,0.3);line-height:1.6;margin:16px 0 0;">{fine_print}</p>'''

    store_badge_html = ''
    if show_store_badge:
        store_badge_html = '''
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
          <tr>
            <td align="center" style="padding: 24px 28px 8px;">
              <a href="https://play.google.com/store/apps/details?id=com.sharppicksllc.app"
                 style="text-decoration:none;" target="_blank">
                <img src="https://play.google.com/intl/en_us/badges/static/images/badges/en_badge_web_generic.png"
                     alt="Get it on Google Play"
                     style="height:40px; border:0;" height="40">
              </a>
            </td>
          </tr>
        </table>'''

    brand = _brand_header_html()

    return f'''<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>SharpPicks</title>
<!--[if mso]><style>table,td{{font-family:Arial,Helvetica,sans-serif!important;}}</style><![endif]-->
</head>
<body style="margin:0;padding:0;background-color:#070B14;-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%;">
<table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color:#070B14;">
  <tr><td align="center" style="padding:0;">
    <table role="presentation" cellpadding="0" cellspacing="0" width="600" style="max-width:600px;width:100%;background-color:#0A0D14;">
      <tr><td style="padding:24px 28px 20px;">
        <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">
          <tr>
            <td>{brand}</td>
            <td align="right" style="font-family:'SF Mono','Menlo','Consolas','Courier New',monospace;font-size:11px;color:rgba(232,234,237,0.35);letter-spacing:0.05em;">{date_str}</td>
          </tr>
        </table>
      </td></tr>
      <tr><td style="padding:0 28px;"><div style="border-top:1px solid rgba(255,255,255,0.06);"></div></td></tr>
      <tr><td style="padding:24px 28px 0;">
        <p style="font-family:'SF Mono','Menlo','Consolas','Courier New',monospace;font-size:11px;font-weight:500;letter-spacing:0.15em;text-transform:uppercase;color:rgba(232,234,237,0.4);margin:0 0 16px;">{type_label}</p>
        {body_html}
        {cta_html}
        {fine_html}
      </td></tr>
      {store_badge_html}
      <tr><td style="padding:24px 28px 28px;">
        <div style="border-top:1px solid rgba(255,255,255,0.06);padding-top:20px;text-align:center;">
          <p style="font-family:Georgia,'Times New Roman',serif;font-style:italic;font-size:12px;color:rgba(232,234,237,0.3);margin:0 0 12px;">One pick beats five.</p>
          <p style="font-family:'SF Pro Display','Helvetica Neue','Arial',sans-serif;font-size:11px;color:rgba(232,234,237,0.25);margin:0 0 4px;">SharpPicks</p>
          <p style="font-family:'SF Mono','Menlo','Consolas','Courier New',monospace;font-size:11px;color:rgba(232,234,237,0.25);margin:0 0 10px;">
            <a href="{base}/" style="color:rgba(232,234,237,0.25);text-decoration:underline;">sharppicks.ai</a>
          </p>
          <p style="font-family:'SF Pro Display','Helvetica Neue','Arial',sans-serif;font-size:11px;color:rgba(232,234,237,0.25);margin:0;">
            <a href="{base}/?view=settings" style="color:rgba(232,234,237,0.25);text-decoration:underline;">Manage preferences</a> &middot;
            <a href="{unsub_url}" style="color:rgba(232,234,237,0.25);text-decoration:underline;">Unsubscribe</a>
          </p>
        </div>
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>'''


# ── 1. Password Reset ──

def send_password_reset(to, reset_url, first_name=None):
    body = '''
        <p style="font-family:'SF Pro Display','Helvetica Neue','Arial',sans-serif;font-size:15px;color:rgba(232,234,237,0.6);line-height:1.6;margin:0;">
          A password reset was requested for this account.
        </p>'''
    html = _base_template(
        'PASSWORD RESET', body,
        cta_text='RESET PASSWORD', cta_url=reset_url,
        fine_print='This link expires in 1 hour. If you did not request this, no action is needed.',
        to_email=to,
    )
    return send_email(to, 'SharpPicks: Password reset requested', html)


# ── 2. Email Verification ──

def send_verification_email(to, verify_url, first_name=None):
    body = '''
        <p style="font-family:'SF Pro Display','Helvetica Neue','Arial',sans-serif;font-size:15px;color:rgba(232,234,237,0.6);line-height:1.6;margin:0;">
          An account was created with this email address. Verify your email to activate access.
        </p>'''
    html = _base_template(
        'ACCOUNT VERIFICATION', body,
        cta_text='VERIFY EMAIL', cta_url=verify_url,
        fine_print='This link expires in 24 hours. If you did not create this account, no action is needed.',
        to_email=to,
    )
    return send_email(to, 'SharpPicks: Verify your email', html)


# ── 3. Welcome / Account Created ──

def send_welcome_email(to, first_name=None):
    base = get_base_url()
    from datetime import datetime
    from zoneinfo import ZoneInfo
    now_et = datetime.now(ZoneInfo('America/New_York'))

    html = _render_jinja('welcome.html', {
        'signal_date': now_et.strftime('%b %d, %Y').upper(),
        'app_url': f'{base}/',
        'guide_url': 'https://sharppicks.ai/guide.html',
        'unsubscribe_url': _make_unsub_url(to),
    })
    if not html:
        body = f'''
        <p style="font-family:'SF Pro Display','Helvetica Neue','Arial',sans-serif;font-size:24px;font-weight:700;color:#E8EAED;margin:0 0 20px;">
          Account active.
        </p>
        <p style="font-family:'SF Pro Display','Helvetica Neue','Arial',sans-serif;font-size:15px;color:rgba(232,234,237,0.6);line-height:1.7;margin:0 0 16px;">
          SharpPicks scans every game on the board and only sends a signal when the model finds a verified, quantified edge above 3.5%. Some days that means no pick at all. That is the product working.
        </p>'''
        html = _base_template(
            'ACCOUNT ACTIVE', body,
            cta_text='OPEN SHARPPICKS', cta_url=f'{base}/',
            to_email=to, show_store_badge=True,
        )
    return send_email(to, 'SharpPicks: Account active', html)


# ── 4. Trial Started ──

def send_trial_started_email(to, trial_start=None, trial_end=None):
    base = get_base_url()
    days = 14
    if trial_start and trial_end:
        days = (trial_end - trial_start).days

    body = '''
        <p style="font-family:'SF Pro Display','Helvetica Neue','Arial',sans-serif;font-size:15px;color:rgba(232,234,237,0.6);line-height:1.6;margin:0;">
          Your trial is active. You will receive signals when the model finds qualifying edges.
        </p>'''
    html = _base_template(
        'TRIAL ACTIVE', body,
        cta_text='OPEN SHARPPICKS', cta_url=f'{base}/',
        fine_print=f'Trial period: {days} days from today.',
        to_email=to,
    )
    return send_email(to, 'SharpPicks: Trial period active', html)


# ── 5. Trial Expiring ──

def send_trial_expiring_email(to, first_name=None, trial_end_date=None, picks_record=None, founding_spots=None):
    base = get_base_url()
    days_left = 1
    if trial_end_date:
        from datetime import datetime
        delta = (trial_end_date - datetime.now()).days
        days_left = max(delta, 1)

    if days_left <= 1:
        label = 'TRIAL EXPIRES TOMORROW'
        body_text = 'Your trial ends tomorrow. Subscribe to keep receiving signals.'
        subject = 'SharpPicks: Trial expires tomorrow'
    else:
        label = f'TRIAL EXPIRES IN {days_left} DAYS'
        body_text = f'Your trial ends in {days_left} days. Subscribe to keep receiving signals.'
        subject = f'SharpPicks: Trial expires in {days_left} days'

    body = f'''
        <p style="font-family:'SF Pro Display','Helvetica Neue','Arial',sans-serif;font-size:15px;color:rgba(232,234,237,0.6);line-height:1.6;margin:0;">
          {body_text}
        </p>'''
    html = _base_template(
        label, body,
        cta_text='SUBSCRIBE', cta_url=f'{base}/subscribe',
        fine_print='After expiration, you will lose access to signal details and result breakdowns.',
        to_email=to,
    )
    return send_email(to, subject, html)


# ── 6. Trial Expired ──

def send_trial_expired_email(to, first_name=None):
    base = get_base_url()
    body = '''
        <p style="font-family:'SF Pro Display','Helvetica Neue','Arial',sans-serif;font-size:15px;color:rgba(232,234,237,0.6);line-height:1.6;margin:0;">
          Your trial has ended. Subscribe to restore access to signals and results.
        </p>'''
    html = _base_template(
        'TRIAL ENDED', body,
        cta_text='SUBSCRIBE', cta_url=f'{base}/subscribe',
        fine_print='Questions: support@sharppicks.ai',
        to_email=to,
    )
    return send_email(to, 'SharpPicks: Trial period ended', html)


# ── 7. Cancellation ──

def send_cancellation_email(to, first_name=None, access_end_date=None, is_founding=False):
    base = get_base_url()
    end_str = access_end_date.strftime('%b %-d, %Y') if access_end_date else 'end of billing period'

    body = '''
        <p style="font-family:'SF Pro Display','Helvetica Neue','Arial',sans-serif;font-size:15px;color:rgba(232,234,237,0.6);line-height:1.6;margin:0;">
          Your subscription has been cancelled. You will retain access until the end of your current billing period.
        </p>'''
    html = _base_template(
        'SUBSCRIPTION CANCELLED', body,
        cta_text='RESUBSCRIBE', cta_url=f'{base}/subscribe',
        fine_print=f'Access ends: {end_str}. Questions: support@sharppicks.ai',
        to_email=to,
    )
    return send_email(to, 'SharpPicks: Subscription cancelled', html)


# ── 8. Payment Failed ──

def send_payment_failed_email(to, first_name=None):
    base = get_base_url()
    body = '''
        <p style="font-family:'SF Pro Display','Helvetica Neue','Arial',sans-serif;font-size:15px;color:rgba(232,234,237,0.6);line-height:1.6;margin:0;">
          We were unable to process your latest payment. Update your payment method to maintain access.
        </p>'''
    html = _base_template(
        'PAYMENT ISSUE', body,
        cta_text='UPDATE PAYMENT', cta_url=f'{base}/',
        fine_print='If this is resolved, disregard this email. Questions: support@sharppicks.ai',
        to_email=to,
    )
    return send_email(to, 'SharpPicks: Payment issue', html)


# ── 9. Signal Generated ──

def send_signal_email(to, pick):
    if not check_email_pref(to, 'email_signals'):
        logging.info(f"Skipping signal email to {to} — unsubscribed")
        return False
    base = get_base_url()
    d = pick if isinstance(pick, dict) else None

    side = (d.get('side', '') if d else (pick.side or ''))
    edge = float(d.get('edge_pct', 0) if d else (pick.edge_pct or 0))
    model_prob_raw = (d.get('cover_prob') or d.get('model_confidence', 0)) if d else (pick.cover_prob or getattr(pick, 'model_confidence', 0) or 0)
    market_prob_raw = float(d.get('implied_prob', 0) if d else (pick.implied_prob or 0))
    margin = d.get('predicted_margin') if d else getattr(pick, 'predicted_margin', None)
    sportsbook = (d.get('sportsbook', 'DraftKings') if d else (pick.sportsbook or 'DraftKings'))

    home_team = (d.get('home_team', '') if d else getattr(pick, 'home_team', ''))
    away_team = (d.get('away_team', '') if d else getattr(pick, 'away_team', ''))

    model_prob = round(float(model_prob_raw) * 100, 1)
    market_prob = round(float(market_prob_raw) * 100, 1)

    from utils.email_helpers import get_edge_strength, fmt_line
    from notification_service import _abbr
    from datetime import datetime
    from zoneinfo import ZoneInfo
    now_et = datetime.now(ZoneInfo('America/New_York'))

    away_parts = away_team.rsplit(' ', 1) if away_team else ['', '']
    home_parts = home_team.rsplit(' ', 1) if home_team else ['', '']

    ctx = _get_shared_email_context()
    ctx.update({
        'away_team_abbr': (d.get('away_abbr', '') if d else getattr(pick, 'away_abbr', '')) or _abbr(away_team),
        'away_team_city': away_parts[0] if len(away_parts) > 1 else '',
        'away_team_name': away_parts[-1] if away_parts else '',
        'home_team_abbr': (d.get('home_abbr', '') if d else getattr(pick, 'home_abbr', '')) or _abbr(home_team),
        'home_team_city': home_parts[0] if len(home_parts) > 1 else '',
        'home_team_name': home_parts[-1] if home_parts else '',
        'game_time': d.get('game_time', '') if d else getattr(pick, 'game_time', ''),
        'pick_team': side,
        'pick_line': fmt_line(d.get('line') if d else getattr(pick, 'line', None)),
        'edge_pct': round(edge, 1),
        'model_prob': model_prob,
        'market_prob': market_prob,
        'calibrated_edge': round(edge, 1),
        'margin_projection': round(float(margin), 1) if margin is not None else None,
        'sportsbook': sportsbook,
        'edge_strength': get_edge_strength(edge),
        'signal_date': now_et.strftime('%b %d, %Y').upper(),
        'signal_time': now_et.strftime('%-I:%M %p EST'),
        'app_url': f'{base}/',
        'unsubscribe_url': _make_unsub_url(to, 'email_signals'),
    })

    html = _render_jinja('signal.html', ctx)
    if not html:
        body = f'''
        <p style="font-family:'SF Pro Display','Helvetica Neue','Arial',sans-serif;font-size:28px;font-weight:700;color:#E8EAED;margin:0 0 8px;">{side}</p>
        <p style="font-family:'SF Mono','Menlo','Consolas','Courier New',monospace;font-size:24px;font-weight:700;color:#5A9E72;margin:0 0 20px;">+{edge:.1f}% edge</p>
        <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:0 0 20px;">
          <tr>
            <td style="padding:12px 0;border-bottom:1px solid rgba(255,255,255,0.06);font-family:'SF Mono','Menlo','Consolas','Courier New',monospace;font-size:14px;color:rgba(232,234,237,0.45);">Model probability</td>
            <td align="right" style="padding:12px 0;border-bottom:1px solid rgba(255,255,255,0.06);font-family:'SF Mono','Menlo','Consolas','Courier New',monospace;font-size:14px;font-weight:500;color:#5A9E72;">{model_prob:.1f}%</td>
          </tr>
          <tr>
            <td style="padding:12px 0;font-family:'SF Mono','Menlo','Consolas','Courier New',monospace;font-size:14px;color:rgba(232,234,237,0.45);">Market probability</td>
            <td align="right" style="padding:12px 0;font-family:'SF Mono','Menlo','Consolas','Courier New',monospace;font-size:14px;font-weight:500;color:#E8EAED;">{market_prob:.1f}%</td>
          </tr>
        </table>'''
        html = _base_template(
            'NEW SIGNAL', body,
            cta_text='VIEW FULL ANALYSIS', cta_url=f'{base}/',
            to_email=to, unsub_category='email_signals',
            show_store_badge=True,
        )
    return send_email(to, f'SharpPicks: {side} Signal', html)


def send_free_signal_email(to, sport='nba', first_name=None):
    """Send a generic signal notification to free-tier users (no pick details)."""
    if not check_email_pref(to, 'email_signals'):
        return False
    base = get_base_url()
    sport_label = sport.upper() if sport else 'NBA'
    greeting = f'{first_name}, a' if first_name else 'A'
    body = f'''
        <p style="font-family:'SF Pro Display','Helvetica Neue','Arial',sans-serif;font-size:15px;color:rgba(232,234,237,0.6);line-height:1.6;margin:0 0 16px;">
          {greeting} qualifying {sport_label} signal was published today. The model found an edge above threshold.
        </p>
        <p style="font-family:'SF Pro Display','Helvetica Neue','Arial',sans-serif;font-size:15px;color:rgba(232,234,237,0.6);line-height:1.6;margin:0;">
          Upgrade to Pro to see the full pick, edge analysis, and track outcomes.
        </p>'''
    html = _base_template(
        f'{sport_label} SIGNAL PUBLISHED', body,
        cta_text='UPGRADE TO PRO', cta_url=f'{base}/?view=signup',
        to_email=to, unsub_category='email_signals',
        show_store_badge=True,
    )
    return send_email(to, f'SharpPicks: {sport_label} signal published today', html)


# ── 10. Signal Result ──

def send_result_email(to, pick):
    if not check_email_pref(to, 'email_results'):
        logging.info(f"Skipping result email to {to} — unsubscribed")
        return False
    base = get_base_url()
    d = pick if isinstance(pick, dict) else None

    side = (d.get('side', '') if d else (pick.side or ''))
    result = (d.get('result', '') if d else (pick.result or ''))
    signal_line = d.get('line') if d else getattr(pick, 'line', None)
    closing = d.get('closing_spread') if d else getattr(pick, 'closing_spread', None)
    clv_val = d.get('clv') if d else getattr(pick, 'clv', None)
    edge = float(d.get('edge_pct', 0) if d else (pick.edge_pct or 0))
    model_prob_raw = (d.get('cover_prob') or d.get('model_confidence', 0)) if d else (pick.cover_prob or getattr(pick, 'model_confidence', 0) or 0)
    home_score = d.get('home_score') if d else getattr(pick, 'home_score', None)
    away_score = d.get('away_score') if d else getattr(pick, 'away_score', None)
    line_open = d.get('line_open') if d else getattr(pick, 'line_open', None)

    is_win = result == 'win'
    is_push = result == 'push'
    result_letter = 'W' if is_win else ('L' if result == 'loss' else 'P')
    result_label = result.upper() if result else 'PENDING'

    from utils.email_helpers import fmt_line

    opening_line_fmt = fmt_line(line_open if line_open is not None else signal_line)
    closing_line_fmt = fmt_line(closing)
    clv_points = round(float(clv_val), 1) if clv_val is not None else 0
    model_prob = round(float(model_prob_raw) * 100, 1) if model_prob_raw else 0

    cover_margin = None
    if home_score is not None and away_score is not None and signal_line is not None:
        spread = float(signal_line)
        actual_margin = float(away_score) - float(home_score)
        cover_margin = round(actual_margin + spread, 1)

    try:
        from models import Pick
        all_settled = Pick.query.filter(Pick.result.in_(['win', 'loss'])).all()
        updated_wins = sum(1 for p in all_settled if p.result == 'win')
        updated_losses = sum(1 for p in all_settled if p.result == 'loss')
        decided = updated_wins + updated_losses
        pnl = sum(p.profit_units or 0 for p in all_settled)
        updated_roi = round((pnl / decided) * 100, 1) if decided else 0

        clv_vals = [p.clv for p in all_settled if p.clv is not None]
        clv_pos = sum(1 for v in clv_vals if v > 0)
        updated_clv = round(clv_pos / len(clv_vals) * 100, 1) if clv_vals else 0
    except Exception:
        updated_wins = updated_losses = 0
        updated_roi = updated_clv = 0

    home_team = (d.get('home_team', '') if d else getattr(pick, 'home_team', ''))
    away_team = (d.get('away_team', '') if d else getattr(pick, 'away_team', ''))
    profit = d.get('profit_units') if d else getattr(pick, 'profit_units', None)

    from notification_service import _abbr
    from datetime import datetime
    from zoneinfo import ZoneInfo
    now_et = datetime.now(ZoneInfo('America/New_York'))

    ctx = _get_shared_email_context()
    ctx.update({
        'result': result_letter,
        'pick_team': side,
        'pick_line': fmt_line(signal_line),
        'away_team_abbr': _abbr(away_team),
        'home_team_abbr': _abbr(home_team),
        'final_score_away': away_score if away_score is not None else '--',
        'final_score_home': home_score if home_score is not None else '--',
        'cover_margin': cover_margin,
        'opening_line': opening_line_fmt,
        'closing_line': closing_line_fmt,
        'clv_points': clv_points,
        'edge_at_entry': round(edge, 1),
        'model_prob': model_prob,
        'profit_units': round(float(profit), 2) if profit is not None else None,
        'updated_wins': updated_wins,
        'updated_losses': updated_losses,
        'updated_clv': updated_clv,
        'updated_roi': updated_roi,
        'signal_date': now_et.strftime('%b %d, %Y'),
        'app_url': f'{base}/',
        'unsubscribe_url': _make_unsub_url(to, 'email_results'),
    })

    html = _render_jinja('grading.html', ctx)
    if not html:
        badge_bg = '#5A9E72' if is_win else ('#8B6F70' if result == 'loss' else 'rgba(232,234,237,0.08)')
        badge_text_color = '#E8EAED' if (is_win or result == 'loss') else 'rgba(232,234,237,0.5)'
        accent = '#5A9E72' if is_win else ('#8B6F70' if result == 'loss' else 'rgba(232,234,237,0.4)')
        profit_val = profit if profit is not None else 0
        units_str = f'+{profit_val:.1f}u' if is_win else (f'{profit_val:.1f}u' if result == 'loss' else '0.0u')
        body = f'''
        <div style="display:inline-block;font-family:'SF Mono','Menlo','Consolas','Courier New',monospace;font-size:11px;font-weight:500;padding:6px 14px;border-radius:4px;letter-spacing:0.15em;text-transform:uppercase;background-color:{badge_bg};color:{badge_text_color};">
          {result_label}
        </div>
        <p style="font-family:'SF Pro Display','Helvetica Neue','Arial',sans-serif;font-size:28px;font-weight:700;color:#E8EAED;margin:20px 0 8px;">
          {side}
        </p>
        <p style="font-family:'SF Pro Display','Helvetica Neue','Arial',sans-serif;font-size:32px;font-weight:700;color:{accent};margin:0 0 20px;">
          {units_str}
        </p>'''
        html = _base_template(
            'SIGNAL RESULT', body,
            cta_text='VIEW FULL RESULTS', cta_url=f'{base}/',
            to_email=to, unsub_category='email_results',
            show_store_badge=True,
        )

    profit = d.get('profit_units') if d else getattr(pick, 'profit_units', None)
    if is_win:
        pnl_sub = f" +{profit:.1f}u" if profit is not None else ""
        subj = f"SharpPicks: {side} \u00b7 Win{pnl_sub}"
    elif result == 'loss':
        pnl_sub = f" {profit:.1f}u" if profit is not None else ""
        subj = f"SharpPicks: {side} \u00b7 Loss{pnl_sub}"
    else:
        subj = f"SharpPicks: {side} \u00b7 Push"
    return send_email(to, subj, html)


# ── 11. Weekly Recap ──

def send_weekly_summary(to, first_name=None, stats=None):
    if not check_email_pref(to, 'email_weekly'):
        logging.info(f"Skipping weekly summary email to {to} — unsubscribed")
        return False
    base = get_base_url()
    s = stats or {}
    wins = s.get('wins', 0)
    losses = s.get('losses', 0)
    picks_made = s.get('picks_made', 0)
    passes = s.get('passes', 0)
    roi = s.get('roi', 0)
    total_record = s.get('total_record', '')
    units = s.get('units', 0)
    avg_edge = s.get('avg_edge', 0)

    record_str = f'{wins}-{losses}'
    units_str = f'{"+" if units >= 0 else ""}{units:.1f}u'

    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    now_et = datetime.now(ZoneInfo('America/New_York'))
    today = now_et.date()
    days_since_monday = today.weekday()
    ws = today - timedelta(days=days_since_monday + 7)
    we = ws + timedelta(days=6)
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    week_start_fmt = f"{months[ws.month - 1]} {ws.day}"
    week_end_fmt = f"{months[we.month - 1]} {we.day}, {we.year}"

    weekly_picks_list = []
    weekly_clv = 0
    season_win_pct = 0
    season_roi = 0
    try:
        from models import Pick
        week_picks = Pick.query.filter(
            Pick.game_date >= ws.strftime('%Y-%m-%d'),
            Pick.game_date <= we.strftime('%Y-%m-%d'),
            Pick.result.in_(['win', 'loss']),
        ).order_by(Pick.game_date).all()

        clv_vals_week = [p.clv for p in week_picks if p.clv is not None]
        weekly_clv = round(sum(clv_vals_week) / len(clv_vals_week), 1) if clv_vals_week else 0

        for p in week_picks:
            from utils.email_helpers import fmt_line
            weekly_picks_list.append({
                'result': 'W' if p.result == 'win' else 'L',
                'team': (p.side or '').split(' ')[-1] if p.side else '',
                'line': fmt_line(p.line),
                'score_away': p.away_score if p.away_score is not None else '--',
                'score_home': p.home_score if p.home_score is not None else '--',
                'cover_margin': round(float(p.away_score or 0) - float(p.home_score or 0) + float(p.line or 0), 1) if p.away_score is not None and p.home_score is not None else None,
                'edge': round(p.edge_pct or 0, 1),
                'clv': round(float(p.clv), 1) if p.clv is not None else None,
            })

        all_settled = Pick.query.filter(Pick.result.in_(['win', 'loss'])).all()
        s_wins = sum(1 for p in all_settled if p.result == 'win')
        s_losses = sum(1 for p in all_settled if p.result == 'loss')
        s_decided = s_wins + s_losses
        season_win_pct = round(s_wins / s_decided * 100, 1) if s_decided else 0
        s_pnl = sum(p.profit_units or 0 for p in all_settled)
        season_roi = round((s_pnl / s_decided) * 100, 1) if s_decided else 0

        clv_all = [p.clv for p in all_settled if p.clv is not None]
        clv_pos = sum(1 for v in clv_all if v > 0)
        season_clv_pct = round(clv_pos / len(clv_all) * 100, 1) if clv_all else 0
    except Exception as e:
        logging.warning(f"Weekly recap enrichment failed: {e}")
        s_wins = s_losses = 0
        season_clv_pct = 0

    ctx = _get_shared_email_context()
    ctx.update({
        'week_num': s.get('week_num', ''),
        'week_start': week_start_fmt,
        'week_end': week_end_fmt,
        'weekly_wins': wins,
        'weekly_losses': losses,
        'weekly_units': round(units, 1),
        'weekly_roi': round(roi, 1),
        'weekly_avg_edge': round(avg_edge, 1),
        'weekly_clv': weekly_clv,
        'picks': weekly_picks_list,
        'season_wins': ctx.get('season_record_wins', s_wins),
        'season_losses': ctx.get('season_record_losses', s_losses),
        'season_win_pct': season_win_pct,
        'season_clv': season_clv_pct if season_clv_pct else ctx.get('season_clv', 0),
        'season_roi': season_roi,
        'pass_days': passes,
        'selectivity': round((picks_made / 7) * 100) if picks_made else 0,
        'app_url': f'{base}/',
        'unsubscribe_url': _make_unsub_url(to, 'email_weekly'),
    })

    html = _render_jinja('weekly_recap.html', ctx)
    if not html:
        roi_color = '#5A9E72' if roi >= 0 else '#8B6F70'
        units_color = '#5A9E72' if units >= 0 else '#8B6F70'
        body = f'''
        <div style="display:inline-block;font-family:'SF Mono','Menlo','Consolas','Courier New',monospace;font-size:11px;font-weight:500;padding:6px 14px;border-radius:4px;letter-spacing:0.15em;text-transform:uppercase;background-color:rgba(232,234,237,0.08);color:rgba(232,234,237,0.5);">
          WEEKLY RECAP
        </div>
        <div style="text-align:center;margin:24px 0;">
          <div style="font-family:'SF Mono','Menlo','Consolas','Courier New',monospace;font-size:40px;font-weight:700;color:{units_color};line-height:1;">{units_str}</div>
          <div style="font-family:'SF Mono','Menlo','Consolas','Courier New',monospace;font-size:13px;color:rgba(232,234,237,0.35);margin-top:8px;">weekly profit</div>
        </div>
        <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">
          <tr>
            <td width="32%" style="background-color:#111622;border-radius:8px;padding:16px 12px;text-align:center;font-family:'SF Mono','Menlo','Consolas','Courier New',monospace;">
              <div style="font-size:20px;font-weight:700;color:#E8EAED;line-height:1;">{record_str}</div>
              <div style="font-size:10px;color:rgba(232,234,237,0.4);margin-top:6px;letter-spacing:0.1em;text-transform:uppercase;">record</div>
            </td>
            <td width="2%"></td>
            <td width="32%" style="background-color:#111622;border-radius:8px;padding:16px 12px;text-align:center;font-family:'SF Mono','Menlo','Consolas','Courier New',monospace;">
              <div style="font-size:20px;font-weight:700;color:{roi_color};line-height:1;">{roi:+.1f}%</div>
              <div style="font-size:10px;color:rgba(232,234,237,0.4);margin-top:6px;letter-spacing:0.1em;text-transform:uppercase;">ROI</div>
            </td>
            <td width="2%"></td>
            <td width="32%" style="background-color:#111622;border-radius:8px;padding:16px 12px;text-align:center;font-family:'SF Mono','Menlo','Consolas','Courier New',monospace;">
              <div style="font-size:20px;font-weight:700;color:#E8EAED;line-height:1;">+{avg_edge:.1f}%</div>
              <div style="font-size:10px;color:rgba(232,234,237,0.4);margin-top:6px;letter-spacing:0.1em;text-transform:uppercase;">avg edge</div>
            </td>
          </tr>
        </table>'''
        html = _base_template(
            'WEEKLY RECAP', body,
            cta_text='VIEW FULL RESULTS', cta_url=f'{base}/',
            to_email=to, unsub_category='email_weekly',
            show_store_badge=True,
        )

    week_num = s.get('week_num', '')
    subj = f'SharpPicks: Week {week_num} \u00b7 {record_str} \u00b7 {units_str}' if picks_made > 0 else 'SharpPicks: All Pass Week'
    return send_email(to, subj, html, reply_to='evan@sharppicks.ai')


# ── 12. Founding Member Confirmation ──

def send_founding_member_email(to, member_number=None, total=100, joined_date=None):
    base = get_base_url()
    body = '''
        <p style="font-family:'SF Pro Display','Helvetica Neue','Arial',sans-serif;font-size:15px;color:rgba(232,234,237,0.6);line-height:1.6;margin:0;">
          Your founding member status is confirmed. Locked rate: $99/year. This rate is permanent and will not increase.
        </p>'''
    html = _base_template(
        'FOUNDING MEMBER', body,
        cta_text='OPEN SHARPPICKS', cta_url=f'{base}/',
        fine_print='Questions: support@sharppicks.ai',
        to_email=to,
    )
    return send_email(to, 'SharpPicks: Founding member status confirmed', html)


# ── 13. Daily Market Scan Complete (No Signal) ──

def send_no_signal_email(to, games_analyzed=0, edges_detected=0, efficiency=0):
    if not check_email_pref(to, 'email_marketing'):
        logging.info(f"Skipping no-signal email to {to} — unsubscribed")
        return False
    base = get_base_url()
    from datetime import datetime as _dt
    from zoneinfo import ZoneInfo as _ZI
    now_et = _dt.now(_ZI('America/New_York'))

    ctx = _get_shared_email_context()
    s_wins = ctx.get('season_record_wins', 0)
    s_losses = ctx.get('season_record_losses', 0)
    decided = s_wins + s_losses

    try:
        from models import Pick, ModelRun
        pass_count = ModelRun.query.filter(ModelRun.status == 'pass').count()
    except Exception:
        pass_count = 0

    try:
        from models import Pick
        all_settled = Pick.query.filter(Pick.result.in_(['win', 'loss'])).all()
        pnl = sum(p.profit_units or 0 for p in all_settled)
        s_roi = round((pnl / decided) * 100, 1) if decided else 0
    except Exception:
        s_roi = 0

    ctx.update({
        'games_analyzed': games_analyzed,
        'closest_edge': round(efficiency * 0.035, 1) if efficiency and efficiency < 100 else None,
        'season_record': f'{s_wins}-{s_losses}',
        'season_roi': s_roi,
        'pass_days': pass_count,
        'signal_date': now_et.strftime('%b %d, %Y').upper(),
        'app_url': f'{base}/',
        'unsubscribe_url': _make_unsub_url(to, 'email_marketing'),
    })

    html = _render_jinja('no_signal.html', ctx)
    if not html:
        html = _base_template(
            'NO SIGNAL', f'''
            <div style="text-align:center;padding:28px 0 4px;">
              <div style="font-family:'SF Mono','Menlo','Consolas','Courier New',monospace;font-size:48px;font-weight:700;color:rgba(232,234,237,0.25);line-height:1;">{games_analyzed}</div>
              <div style="font-family:'SF Mono','Menlo','Consolas','Courier New',monospace;font-size:13px;color:rgba(232,234,237,0.35);margin-top:8px;">games scanned</div>
            </div>
            <div style="font-family:'SF Pro Display','Helvetica Neue','Arial',sans-serif;font-size:14px;color:rgba(232,234,237,0.5);line-height:1.6;padding:16px 20px;border-left:2px solid rgba(90,158,114,0.3);margin:20px 0;">
              {games_analyzed} games analyzed, none above the 3.5% minimum edge threshold.
            </div>
            <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:20px 0;">
              <tr>
                <td style="background-color:#111622;border:1px solid rgba(90,158,114,0.15);border-radius:8px;padding:20px 24px;text-align:center;">
                  <div style="font-family:'SF Pro Display','Helvetica Neue','Arial',sans-serif;font-size:14px;font-weight:700;color:#5A9E72;margin-bottom:8px;">This is the product working.</div>
                  <div style="font-family:'SF Pro Display','Helvetica Neue','Arial',sans-serif;font-size:13px;color:rgba(232,234,237,0.45);line-height:1.6;">Most services would have picked 3-4 of these games. We require a verified, quantified edge before sending a signal. No edge, no pick.</div>
                </td>
              </tr>
            </table>''',
            cta_text='VIEW MARKET REPORT', cta_url=f'{base}/',
            to_email=to, unsub_category='email_marketing',
        )
    return send_email(to, 'SharpPicks: Market scan complete \u00b7 No qualifying signal', html)


# ── Legacy: Welcome email (preserving for backward compat) ──

def send_welcome(to, first_name=None):
    """Legacy welcome email - redirects to send_welcome_email."""
    return send_welcome_email(to, first_name=first_name)
