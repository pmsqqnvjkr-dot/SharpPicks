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
    """Inline brand header: SHARP || PICKS with green double-bar separator."""
    return (
        '<span style="font-family:\'SF Mono\',\'Menlo\',\'Consolas\',\'Courier New\',monospace;font-size:13px;font-weight:500;'
        'letter-spacing:0.2em;color:#E8EAED;white-space:nowrap;display:inline-flex;align-items:center;line-height:1;">'
        'SHARP'
        '<span style="display:inline-flex;flex-direction:column;align-items:center;margin:0 6px;gap:2px;letter-spacing:0;">'
        '<span style="display:inline-flex;gap:2px;">'
        '<span style="display:inline-block;width:2px;height:16px;background:#E8EAED;border-radius:1px;"></span>'
        '<span style="display:inline-block;width:2px;height:16px;background:#E8EAED;border-radius:1px;"></span>'
        '</span>'
        '<span style="display:inline-block;width:5px;height:1.5px;background:#5A9E72;border-radius:1px;"></span>'
        '</span>'
        'PICKS'
        '</span>'
    )


def _base_template(type_label, body_html, cta_text=None, cta_url=None,
                   fine_print=None, to_email=None, unsub_category='all'):
    base = get_base_url()
    unsub_url = _make_unsub_url(to_email, unsub_category) if to_email else f'{base}/unsubscribe'
    unsub_html = f'''
        <p style="font-family:'SF Pro Display','Helvetica Neue','Arial',sans-serif;font-size:11px;color:rgba(232,234,237,0.25);text-align:center;margin:8px 0 0;">
          <a href="{unsub_url}" style="color:rgba(232,234,237,0.25);text-decoration:underline;">Unsubscribe</a>
        </p>'''

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
        <p style="font-family:'SF Pro Display','Helvetica Neue','Arial',sans-serif;font-size:13px;color:rgba(232,234,237,0.45);line-height:1.6;margin:16px 0 0;">{fine_print}</p>'''

    brand = _brand_header_html()

    return f'''<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>SharpPicks</title></head>
<body style="margin:0;padding:0;background-color:#070B14;">
<table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color:#070B14;">
  <tr><td align="center" style="padding:0;">
    <table role="presentation" cellpadding="0" cellspacing="0" width="600" style="max-width:600px;width:100%;background-color:#0A0D14;">
      <tr><td style="padding:24px 28px 20px;">
        {brand}
      </td></tr>
      <tr><td style="padding:0 28px;"><div style="border-top:1px solid rgba(255,255,255,0.06);"></div></td></tr>
      <tr><td style="padding:24px 28px 0;">
        <p style="font-family:'SF Mono','Menlo','Consolas','Courier New',monospace;font-size:11px;font-weight:500;letter-spacing:0.15em;text-transform:uppercase;color:rgba(232,234,237,0.4);margin:0 0 20px;">{type_label}</p>
        {body_html}
        {cta_html}
        {fine_html}
      </td></tr>
      <tr><td style="padding:24px 28px 28px;">
        <div style="border-top:1px solid rgba(255,255,255,0.06);padding-top:20px;text-align:center;">
          <p style="font-family:Georgia,'Times New Roman',serif;font-style:italic;font-size:12px;color:rgba(232,234,237,0.3);margin:0 0 12px;">One pick beats five.</p>
          <p style="font-family:'SF Pro Display','Helvetica Neue','Arial',sans-serif;font-size:11px;color:rgba(232,234,237,0.25);margin:0 0 4px;">SharpPicks</p>
          <p style="font-family:'SF Mono','Menlo','Consolas','Courier New',monospace;font-size:11px;color:rgba(232,234,237,0.25);margin:0 0 10px;">
            <a href="{base}/" style="color:rgba(232,234,237,0.25);text-decoration:underline;">sharppicks.ai</a>
          </p>
          {unsub_html}
        </div>
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>'''


# ── 1. Password Reset ──

def send_password_reset(to, reset_url, first_name=None):
    unsub_url = _make_unsub_url(to)
    html = _render('password-reset', {
        'firstName': first_name,
        'resetUrl': reset_url,
        'expiresIn': '1 hour',
    })
    if not html:
        body = '''
        <p style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#AAAAAA;line-height:1.7;margin:0 0 16px;">
          A password reset was requested for this account.
        </p>
        <p style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#AAAAAA;line-height:1.7;margin:0 0 24px;">
          Use the link below to set a new password.
        </p>'''
        html = _base_template(
            'ACCOUNT SECURITY', body,
            cta_text='RESET PASSWORD', cta_url=reset_url,
            fine_print='This link expires in 1 hour. If you did not request this, no action is needed.',
            to_email=to,
        )
    return send_email(to, 'SharpPicks: Password reset requested', html)


# ── 2. Email Verification ──

def send_verification_email(to, verify_url, first_name=None):
    html = _render('verification', {
        'firstName': first_name,
        'verifyUrl': verify_url,
    })
    if not html:
        body = '''
        <p style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#AAAAAA;line-height:1.7;margin:0 0 16px;">
          An account was created with this email address.
        </p>
        <p style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#AAAAAA;line-height:1.7;margin:0 0 24px;">
          Verify your email to activate access.
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
        html = _render('welcome', {
            'firstName': first_name,
            'appUrl': f'{base}/',
            'guideUrl': 'https://sharppicks.ai/guide.html',
            'unsubscribeUrl': _make_unsub_url(to),
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
            'ACCOUNT STATUS', body,
            cta_text='OPEN SHARPPICKS', cta_url=f'{base}/',
            to_email=to,
        )
    return send_email(to, 'SharpPicks: Account active', html)


# ── 4. Trial Started ──

def send_trial_started_email(to, trial_start=None, trial_end=None):
    base = get_base_url()
    end_str = trial_end.strftime('%b %-d, %Y') if trial_end else ''
    start_str = trial_start.strftime('%b %-d, %Y') if trial_start else ''

    days = 7
    if trial_start and trial_end:
        days = (trial_end - trial_start).days

    html = _render('trial-started', {
        'firstName': None,
        'trialEndDate': end_str,
        'trialDays': days,
        'appUrl': f'{base}/',
        'unsubscribeUrl': _make_unsub_url(to),
    })
    if not html:
        data_block = ''
        if start_str and end_str:
            data_block = f'''
            <table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:16px 0 24px;">
              <tr><td align="center" style="padding:16px;background-color:#1A1A1A;border-radius:6px;">
                <p style="font-family:'Courier New',Courier,monospace;font-size:15px;color:#FFFFFF;margin:0;">
                  Trial start: {start_str} &middot; Trial end: {end_str}
                </p>
              </td></tr>
            </table>'''
        body = f'''
        <p style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#AAAAAA;line-height:1.7;margin:0 0 16px;">
          Your trial period is now active. You have full access to all signal data, edge analysis, and market intelligence for the next {days} days.
        </p>
        {data_block}'''
        html = _base_template(
            'ACCOUNT STATUS', body,
            cta_text='VIEW TODAY\'S MARKET', cta_url=f'{base}/',
            to_email=to,
        )
    return send_email(to, 'SharpPicks: Trial period active', html)


# ── 5. Trial Expiring ──

def send_trial_expiring_email(to, first_name=None, trial_end_date=None, picks_record=None, founding_spots=None):
    base = get_base_url()
    end_str = trial_end_date.strftime('%b %-d, %Y') if trial_end_date else 'tomorrow'
    days_left = 1
    if trial_end_date:
        from datetime import datetime
        delta = (trial_end_date - datetime.now()).days
        days_left = max(delta, 1)

    html = _render('trial-expiring', {
        'firstName': first_name,
        'daysLeft': days_left,
        'trialEndDate': end_str,
        'upgradeUrl': f'{base}/subscribe',
        'unsubscribeUrl': _make_unsub_url(to),
    })
    if not html:
        body = f'''
        <p style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#AAAAAA;line-height:1.7;margin:0 0 16px;">
          Your trial period ends tomorrow.
        </p>
        <table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:0 0 24px;">
          <tr><td align="center" style="padding:16px;background-color:#1A1A1A;border-radius:6px;">
            <p style="font-family:'Courier New',Courier,monospace;font-size:15px;color:#FFFFFF;margin:0;">
              Trial ends: {end_str}
            </p>
          </td></tr>
        </table>'''
        html = _base_template(
            'ACCOUNT NOTICE', body,
            cta_text='MANAGE SUBSCRIPTION', cta_url=f'{base}/subscribe',
            to_email=to,
        )
    return send_email(to, 'SharpPicks: Trial expires tomorrow', html)


# ── 6. Trial Expired ──

def send_trial_expired_email(to, first_name=None):
    base = get_base_url()
    html = _render('trial-expired', {
        'firstName': first_name,
        'upgradeUrl': f'{base}/subscribe',
        'unsubscribeUrl': _make_unsub_url(to),
    })
    if not html:
        body = '''
        <p style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#AAAAAA;line-height:1.7;margin:0 0 16px;">
          Your trial period has ended. Access has been moved to the free tier.
        </p>'''
        html = _base_template(
            'ACCOUNT STATUS', body,
            cta_text='SUBSCRIBE', cta_url=f'{base}/subscribe',
            to_email=to,
        )
    return send_email(to, 'SharpPicks: Trial period ended', html)


# ── 7. Cancellation ──

def send_cancellation_email(to, first_name=None, access_end_date=None, is_founding=False):
    base = get_base_url()
    end_str = access_end_date.strftime('%b %-d, %Y') if access_end_date else 'end of billing period'

    html = _render('cancellation', {
        'firstName': first_name,
        'accessEndsDate': end_str,
        'reactivateUrl': f'{base}/subscribe',
        'unsubscribeUrl': _make_unsub_url(to),
    })
    if not html:
        body = f'''
        <p style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#AAAAAA;line-height:1.7;margin:0 0 16px;">
          Subscription cancelled. Full access continues through {end_str}.
        </p>'''
        html = _base_template(
            'ACCOUNT STATUS', body,
            cta_text='RESUBSCRIBE', cta_url=f'{base}/subscribe',
            to_email=to,
        )
    return send_email(to, 'SharpPicks: Subscription cancelled', html)


# ── 8. Payment Failed ──

def send_payment_failed_email(to, first_name=None):
    base = get_base_url()
    html = _render('payment-failed', {
        'firstName': first_name,
        'updateUrl': f'{base}/',
        'unsubscribeUrl': _make_unsub_url(to),
    })
    if not html:
        body = '''
        <p style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#AAAAAA;line-height:1.7;margin:0 0 16px;">
          Payment processing failed. Update your payment method to avoid interruption.
        </p>'''
        html = _base_template(
            'BILLING NOTICE', body,
            cta_text='UPDATE PAYMENT', cta_url=f'{base}/',
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
        sport_label = (d.get('sport', 'nba') if d else getattr(pick, 'sport', 'nba') or 'nba').upper()
        html = _render('signal', {
            'sport': sport_label, 'matchup': f'{away_team} vs {home_team}',
            'market': side, 'edge': f'+{edge:.1f}%', 'price': sportsbook,
            'startTime': '', 'modelPct': model_prob, 'marketPct': market_prob,
            'margin': round(float(margin), 1) if margin is not None else None,
            'appUrl': f'{base}/', 'unsubscribeUrl': _make_unsub_url(to, 'email_signals'),
        })
    if not html:
        body = f'''
        <p style="font-family:Arial,Helvetica,sans-serif;font-size:22px;font-weight:bold;color:#FFFFFF;margin:0 0 8px;">{side}</p>
        <p style="font-family:Arial,Helvetica,sans-serif;font-size:18px;font-weight:bold;color:#5A9E72;margin:0 0 20px;">Edge: +{edge:.1f}%</p>
        <table cellpadding="0" cellspacing="0" border="0" style="margin:0 0 20px;">
          <tr><td style="padding:4px 0;font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#FFFFFF;">Model: {model_prob:.1f}%</td></tr>
          <tr><td style="padding:4px 0;font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#FFFFFF;">Market: {market_prob:.1f}%</td></tr>
        </table>'''
        html = _base_template(
            'SIGNAL GENERATED', body,
            cta_text='VIEW FULL ANALYSIS', cta_url=f'{base}/',
            fine_print='This signal was generated by the SharpPicks model. Past performance does not guarantee future results.',
            to_email=to, unsub_category='email_signals',
        )
    return send_email(to, f'SharpPicks: {side} Signal', html)


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
        result_color = '#5A9E72' if is_win else ('#9E7A7C' if result == 'loss' else '#666666')
        icon = '&#x2714;' if is_win else ('&#x2014;' if is_push else '&#x2718;')
        body = f'''
        <p style="font-family:Arial,Helvetica,sans-serif;font-size:22px;font-weight:bold;color:#FFFFFF;margin:0 0 8px;">
          {side} &nbsp;<span style="color:{result_color};">{icon}</span>
        </p>
        <p style="font-family:Arial,Helvetica,sans-serif;font-size:16px;color:{result_color};font-weight:bold;margin:0 0 20px;">
          Result: {result_label}
        </p>'''
        html = _base_template(
            'SIGNAL RESULT', body,
            cta_text='VIEW FULL RESULTS', cta_url=f'{base}/',
            to_email=to, unsub_category='email_results',
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
        roi_color = '#5A9E72' if roi >= 0 else '#9E7A7C'
        body = f'''
        <table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:0 0 8px;">
          <tr>
            <td style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#FFFFFF;padding:6px 0;">Record: <strong>{record_str}</strong></td>
            <td align="right" style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:{roi_color};padding:6px 0;">ROI: {roi:+.1f}%</td>
          </tr>
          <tr>
            <td style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#FFFFFF;padding:6px 0;">Units: {units_str}</td>
            <td align="right" style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#FFFFFF;padding:6px 0;">Avg Edge: +{avg_edge:.1f}%</td>
          </tr>
        </table>
        <p style="font-family:Arial,Helvetica,sans-serif;font-size:13px;color:#AAAAAA;margin:8px 0 20px;">
          Days passed this week: {passes}
        </p>'''
        html = _base_template(
            'WEEKLY REPORT', body,
            cta_text='VIEW FULL REPORT', cta_url=f'{base}/',
            to_email=to, unsub_category='email_weekly',
        )

    week_num = s.get('week_num', '')
    subj = f'SharpPicks: Week {week_num} \u00b7 {record_str} \u00b7 {units_str}' if picks_made > 0 else 'SharpPicks: All Pass Week'
    return send_email(to, subj, html, reply_to='evan@sharppicks.ai')


# ── 12. Founding Member Confirmation ──

def send_founding_member_email(to, member_number=None, total=100, joined_date=None):
    base = get_base_url()
    html = _render('founding-member', {
        'firstName': None,
        'foundingNumber': member_number,
        'appUrl': f'{base}/',
        'unsubscribeUrl': _make_unsub_url(to),
    })
    if not html:
        num = member_number or '—'
        body = f'''
        <p style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#AAAAAA;line-height:1.7;margin:0 0 16px;">
          Your founding member status has been confirmed.
        </p>
        <table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:0 0 24px;">
          <tr><td align="center" style="padding:20px;background-color:#1A1A1A;border-radius:6px;">
            <p style="font-family:'Courier New',Courier,monospace;font-size:28px;font-weight:bold;color:#FFFFFF;margin:0 0 8px;">
              #{num} of {total}
            </p>
          </td></tr>
        </table>'''
        html = _base_template(
            'MEMBER STATUS', body,
            cta_text='ENTER MARKET VIEW', cta_url=f'{base}/',
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
            <p style="font-family:'Courier New',Courier,monospace;font-size:15px;color:#AAAAAA;line-height:1.7;margin:0 0 16px;">
              {games_analyzed} games scanned, none above threshold.
            </p>''',
            cta_text='VIEW MARKET REPORT', cta_url=f'{base}/',
            to_email=to, unsub_category='email_marketing',
        )
    return send_email(to, 'SharpPicks: Market scan complete \u00b7 No qualifying signal', html)


# ── Legacy: Welcome email (preserving for backward compat) ──

def send_welcome(to, first_name=None):
    """Legacy welcome email - redirects to send_welcome_email."""
    return send_welcome_email(to, first_name=first_name)
