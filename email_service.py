import os
import base64
import logging
import resend

resend.api_key = os.environ.get('RESEND_API_KEY', '')

FROM_EMAIL = "SharpPicks <info@sharppicks.ai>"
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


# ── Shared email base template ──
# Dark terminal aesthetic, table-based for Outlook, inline CSS.

def _base_template(type_label, body_html, cta_text=None, cta_url=None,
                   fine_print=None, unsubscribe=False):
    base = get_base_url()
    unsub_html = ''
    if unsubscribe:
        unsub_html = f'''
        <p style="font-family:Arial,Helvetica,sans-serif;font-size:12px;color:#444444;text-align:center;margin:8px 0 0;">
          <a href="{base}/unsubscribe" style="color:#4A9EFF;text-decoration:underline;">Unsubscribe</a>
          &nbsp;&middot;&nbsp;
          <a href="{base}/preferences" style="color:#4A9EFF;text-decoration:underline;">Manage preferences</a>
        </p>'''

    cta_html = ''
    if cta_text and cta_url:
        cta_html = f'''
        <table cellpadding="0" cellspacing="0" border="0" style="margin:32px auto;">
          <tr>
            <td align="center" bgcolor="#5A9E72" style="border-radius:6px;">
              <!--[if mso]>
              <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="urn:schemas-microsoft-com:office:word"
                href="{cta_url}" style="height:46px;v-text-anchor:middle;width:220px;" arcsize="13%" strokecolor="#5A9E72" fillcolor="#5A9E72">
              <w:anchorlock/><center style="color:#ffffff;font-family:Arial,sans-serif;font-size:14px;font-weight:bold;letter-spacing:0.05em;">{cta_text}</center>
              </v:roundrect>
              <![endif]-->
              <!--[if !mso]><!-->
              <a href="{cta_url}" style="display:inline-block;padding:14px 32px;background-color:#5A9E72;color:#ffffff;text-decoration:none;border-radius:6px;font-family:Arial,Helvetica,sans-serif;font-size:14px;font-weight:bold;letter-spacing:0.05em;text-transform:uppercase;">{cta_text}</a>
              <!--<![endif]-->
            </td>
          </tr>
        </table>'''

    fine_html = ''
    if fine_print:
        fine_html = f'''
        <p style="font-family:Arial,Helvetica,sans-serif;font-size:12px;color:#666666;line-height:1.6;margin:0 0 24px;">{fine_print}</p>'''

    return f'''<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>SharpPicks</title></head>
<body style="margin:0;padding:0;background-color:#0D0D0D;">
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color:#0D0D0D;">
  <tr><td align="center" style="padding:32px 16px;">
    <table cellpadding="0" cellspacing="0" border="0" width="560" style="max-width:560px;background-color:#141414;border-radius:8px;">
      <tr><td style="padding:32px 32px 0;">
        <table cellpadding="0" cellspacing="0" border="0" width="100%">
          <tr><td align="center" style="padding:0 0 16px;">
            <img src="{base}/images/crest.png" alt="" width="28" height="28" style="display:inline-block;vertical-align:middle;margin-right:12px;" /><!--
            --><span style="font-family:Arial,Helvetica,sans-serif;font-size:13px;font-weight:800;letter-spacing:0.3em;text-transform:uppercase;color:#FFFFFF;vertical-align:middle;">SHARP<span style="opacity:0.5;margin:0 0.35em;font-weight:500;letter-spacing:0.15em;">||</span>PICKS</span>
          </td></tr>
        </table>
        <hr style="border:none;border-top:1px solid #2A2A2A;margin:0 0 24px;">
      </td></tr>
      <tr><td style="padding:0 32px;">
        <p style="font-family:Arial,Helvetica,sans-serif;font-size:11px;font-weight:bold;letter-spacing:0.1em;text-transform:uppercase;color:#666666;margin:0 0 20px;">{type_label}</p>
        {body_html}
        {cta_html}
        {fine_html}
      </td></tr>
      <tr><td style="padding:0 32px 32px;">
        <hr style="border:none;border-top:1px solid #2A2A2A;margin:24px 0 16px;">
        <p style="font-family:Arial,Helvetica,sans-serif;font-size:12px;color:#444444;text-align:center;margin:0;">
          SharpPicks &mdash; Discipline is the product.
        </p>
        <p style="font-family:Arial,Helvetica,sans-serif;font-size:12px;color:#444444;text-align:center;margin:8px 0 0;">
          support@sharppicks.ai
        </p>
        {unsub_html}
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>'''


# ── 1. Password Reset ──

def send_password_reset(to, reset_url, first_name=None):
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
    )
    return send_email(to, 'SharpPicks \u2014 Password reset requested', html)


# ── 2. Email Verification ──

def send_verification_email(to, verify_url, first_name=None):
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
    )
    return send_email(to, 'SharpPicks \u2014 Verify your email', html)


# ── 3. Welcome / Account Created ──

def send_welcome_email(to, first_name=None):
    base = get_base_url()
    body = '''
    <p style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#AAAAAA;line-height:1.7;margin:0 0 16px;">
      Your account is active.
    </p>
    <p style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#AAAAAA;line-height:1.7;margin:0 0 16px;">
      SharpPicks scans the full NBA market daily and generates signals only when a statistically significant edge is detected. Most days produce few or zero signals.
    </p>
    <p style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#AAAAAA;line-height:1.7;margin:0 0 24px;">
      That&rsquo;s by design.
    </p>'''

    html = _base_template(
        'ACCOUNT STATUS', body,
        cta_text='ENTER MARKET VIEW', cta_url=f'{base}/',
        fine_print='Questions? Reply to this email or contact support@sharppicks.ai',
    )
    return send_email(to, 'SharpPicks \u2014 Account active', html)


# ── 4. Trial Started ──

def send_trial_started_email(to, trial_start=None, trial_end=None):
    base = get_base_url()
    start_str = trial_start.strftime('%b %-d, %Y') if trial_start else ''
    end_str = trial_end.strftime('%b %-d, %Y') if trial_end else ''

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
      Your trial period is now active. You have full access to all signal data, edge analysis, and market intelligence for the next 7 days.
    </p>
    <p style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#AAAAAA;line-height:1.7;margin:0 0 16px;">
      Signals are generated selectively &mdash; if no qualifying edge is detected, no signal is published.
    </p>
    {data_block}'''

    html = _base_template(
        'ACCOUNT STATUS', body,
        cta_text='VIEW TODAY\'S MARKET', cta_url=f'{base}/',
        fine_print=f'Your trial will convert to a paid subscription on {end_str} unless cancelled.' if end_str else None,
    )
    return send_email(to, 'SharpPicks \u2014 Trial period active', html)


# ── 5. Trial Expiring ──

def send_trial_expiring_email(to, first_name=None, trial_end_date=None, picks_record=None, founding_spots=None):
    base = get_base_url()
    end_str = trial_end_date.strftime('%b %-d, %Y') if trial_end_date else 'tomorrow'

    body = f'''
    <p style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#AAAAAA;line-height:1.7;margin:0 0 16px;">
      Your trial period ends tomorrow. To maintain access to signal data and market analysis, your subscription will activate automatically.
    </p>
    <p style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#AAAAAA;line-height:1.7;margin:0 0 24px;">
      No action needed to continue.
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
        fine_print='To cancel, manage your subscription before the trial end date.',
    )
    return send_email(to, 'SharpPicks \u2014 Trial expires tomorrow', html)


# ── 6. Trial Expired ──

def send_trial_expired_email(to, first_name=None):
    base = get_base_url()
    body = '''
    <p style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#AAAAAA;line-height:1.7;margin:0 0 16px;">
      Your trial period has ended. Access has been moved to the free tier.
    </p>
    <p style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#AAAAAA;line-height:1.7;margin:0 0 24px;">
      Subscribe to restore full signal data, edge analysis, and performance tracking.
    </p>'''

    html = _base_template(
        'ACCOUNT STATUS', body,
        cta_text='SUBSCRIBE', cta_url=f'{base}/subscribe',
    )
    return send_email(to, 'SharpPicks \u2014 Trial period ended', html)


# ── 7. Cancellation ──

def send_cancellation_email(to, first_name=None, access_end_date=None, is_founding=False):
    base = get_base_url()
    end_str = access_end_date.strftime('%b %-d, %Y') if access_end_date else 'end of billing period'

    founding_warning = ''
    if is_founding:
        founding_warning = '''
        <table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:0 0 16px;">
          <tr><td style="padding:14px 16px;background-color:rgba(204,51,51,0.06);border:1px solid rgba(204,51,51,0.2);border-radius:6px;">
            <p style="font-family:Arial,Helvetica,sans-serif;font-size:14px;color:#CC3333;font-weight:bold;margin:0;">
              Founding member rate cannot be restored if you resubscribe later.
            </p>
          </td></tr>
        </table>'''

    body = f'''
    <p style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#AAAAAA;line-height:1.7;margin:0 0 16px;">
      Subscription cancelled. Full access continues through {end_str}.
    </p>
    <p style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#AAAAAA;line-height:1.7;margin:0 0 16px;">
      After that date, access moves to the free tier.
    </p>
    {founding_warning}'''

    html = _base_template(
        'ACCOUNT STATUS', body,
        cta_text='RESUBSCRIBE', cta_url=f'{base}/subscribe',
    )
    return send_email(to, 'SharpPicks \u2014 Subscription cancelled', html)


# ── 8. Payment Failed ──

def send_payment_failed_email(to, first_name=None):
    base = get_base_url()
    body = '''
    <p style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#AAAAAA;line-height:1.7;margin:0 0 16px;">
      Payment processing failed. The provider will retry automatically.
    </p>
    <p style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#AAAAAA;line-height:1.7;margin:0 0 24px;">
      Update your payment method to avoid interruption.
    </p>'''

    html = _base_template(
        'BILLING NOTICE', body,
        cta_text='UPDATE PAYMENT', cta_url=f'{base}/',
    )
    return send_email(to, 'SharpPicks \u2014 Payment issue', html)


# ── 9. Signal Generated (P0 — most important email) ──

def send_signal_email(to, pick):
    base = get_base_url()
    side = pick.get('side', '') if isinstance(pick, dict) else (pick.side or '')
    edge = pick.get('edge_pct', 0) if isinstance(pick, dict) else (pick.edge_pct or 0)
    model_prob = pick.get('cover_prob') or pick.get('model_confidence', 0) if isinstance(pick, dict) else (pick.cover_prob or pick.model_confidence or 0)
    market_prob = pick.get('implied_prob', 0) if isinstance(pick, dict) else (pick.implied_prob or 0)
    margin = pick.get('predicted_margin') if isinstance(pick, dict) else getattr(pick, 'predicted_margin', None)
    sportsbook = pick.get('sportsbook', 'DraftKings') if isinstance(pick, dict) else (pick.sportsbook or 'DraftKings')
    signal_time = pick.get('signal_time', '') if isinstance(pick, dict) else ''
    signal_date = pick.get('signal_date', '') if isinstance(pick, dict) else ''
    pick_id = pick.get('id', '') if isinstance(pick, dict) else (pick.id or '')

    timestamp = ''
    if signal_time and signal_date:
        timestamp = f'{signal_time} &middot; {signal_date}'
    elif signal_time:
        timestamp = signal_time

    margin_line = ''
    if margin is not None:
        margin_line = f'''
        <tr><td style="padding:4px 0;font-family:Arial,Helvetica,sans-serif;font-size:13px;color:#AAAAAA;">
          Margin Projection: {"+" if margin > 0 else ""}{margin:.1f}
        </td></tr>'''

    body = f'''
    {f'<p style="font-family:Arial,Helvetica,sans-serif;font-size:13px;color:#666666;margin:0 0 20px;">{timestamp}</p>' if timestamp else ''}
    <p style="font-family:Arial,Helvetica,sans-serif;font-size:22px;font-weight:bold;color:#FFFFFF;margin:0 0 8px;">{side}</p>
    <p style="font-family:Arial,Helvetica,sans-serif;font-size:18px;font-weight:bold;color:#5A9E72;margin:0 0 20px;">Edge: +{edge:.1f}%</p>
    <table cellpadding="0" cellspacing="0" border="0" style="margin:0 0 20px;">
      <tr><td style="padding:4px 0;font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#FFFFFF;">
        Model: {model_prob * 100:.1f}%
      </td></tr>
      <tr><td style="padding:4px 0;font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#FFFFFF;">
        Market: {market_prob * 100:.1f}%
      </td></tr>
    </table>
    <hr style="border:none;border-top:1px solid #2A2A2A;margin:0 0 16px;">
    <table cellpadding="0" cellspacing="0" border="0" style="margin:0 0 20px;">
      <tr><td style="padding:4px 0;font-family:Arial,Helvetica,sans-serif;font-size:13px;color:#AAAAAA;">
        Calibrated Edge: +{edge:.1f}%
      </td></tr>
      {margin_line}
      <tr><td style="padding:4px 0;font-family:Arial,Helvetica,sans-serif;font-size:13px;color:#AAAAAA;">
        Sportsbook: {sportsbook}
      </td></tr>
    </table>'''

    html = _base_template(
        'SIGNAL GENERATED', body,
        cta_text='VIEW FULL ANALYSIS', cta_url=f'{base}/',
        fine_print='This signal was generated by the SharpPicks model. Past performance does not guarantee future results.',
    )
    return send_email(to, f'SharpPicks Signal \u2014 {side}', html)


# ── 10. Signal Result ──

def send_result_email(to, pick):
    base = get_base_url()
    side = pick.get('side', '') if isinstance(pick, dict) else (pick.side or '')
    result = pick.get('result', '') if isinstance(pick, dict) else (pick.result or '')
    units = pick.get('profit_units') if isinstance(pick, dict) else getattr(pick, 'profit_units', None)
    edge = pick.get('edge_pct', 0) if isinstance(pick, dict) else (pick.edge_pct or 0)
    signal_line = pick.get('line') if isinstance(pick, dict) else getattr(pick, 'line', None)
    closing = pick.get('closing_spread') if isinstance(pick, dict) else getattr(pick, 'closing_spread', None)
    clv = pick.get('clv') if isinstance(pick, dict) else getattr(pick, 'clv', None)

    is_win = result == 'win'
    is_push = result == 'push'
    icon = '&#x2714;' if is_win else ('&#x2014;' if is_push else '&#x2718;')
    result_label = result.upper() if result else 'PENDING'
    result_color = '#5A9E72' if is_win else ('#CC3333' if result == 'loss' else '#666666')

    units_str = ''
    if units is not None:
        u = float(units)
        units_str = f'{"+" if u > 0 else ""}{u:.1f}u'
        units_color = '#5A9E72' if u > 0 else ('#CC3333' if u < 0 else '#666666')
    else:
        units_color = '#666666'

    clv_html = ''
    if signal_line is not None or closing is not None or clv is not None:
        clv_html = '<table cellpadding="0" cellspacing="0" border="0" style="margin:0 0 16px;">'
        if signal_line is not None:
            sl = float(signal_line)
            sl_str = f'{int(sl)}' if sl == int(sl) else f'{sl:.1f}'
            sl_str = f'+{sl_str}' if sl > 0 else sl_str
            clv_html += f'<tr><td style="padding:4px 0;font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#FFFFFF;">Signal Line: {sl_str}</td></tr>'
        if closing is not None:
            cl = float(closing)
            cl_str = f'{int(cl)}' if cl == int(cl) else f'{cl:.1f}'
            cl_str = f'+{cl_str}' if cl > 0 else cl_str
            clv_html += f'<tr><td style="padding:4px 0;font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#FFFFFF;">Closing Line: {cl_str}</td></tr>'
        if clv is not None:
            cv = float(clv)
            clv_c = '#5A9E72' if cv > 0 else ('#CC3333' if cv < 0 else '#666666')
            clv_html += f'<tr><td style="padding:4px 0;font-family:Arial,Helvetica,sans-serif;font-size:15px;color:{clv_c};">CLV: {"+" if cv > 0 else ""}{cv:.1f}</td></tr>'
        clv_html += '</table>'

    subject_icon = '\u2714' if is_win else ('\u2718' if result == 'loss' else '\u2014')

    body = f'''
    <p style="font-family:Arial,Helvetica,sans-serif;font-size:22px;font-weight:bold;color:#FFFFFF;margin:0 0 8px;">
      {side} &nbsp;<span style="color:{result_color};">{icon}</span>
    </p>
    <p style="font-family:Arial,Helvetica,sans-serif;font-size:16px;color:{result_color};font-weight:bold;margin:0 0 20px;">
      Result: {result_label}{f" &nbsp;&middot;&nbsp; {units_str}" if units_str else ""}
    </p>
    {clv_html}
    {f'<p style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#FFFFFF;margin:0 0 20px;">Model Edge: +{edge:.1f}%</p>' if edge else ''}'''

    html = _base_template(
        'SIGNAL RESULT', body,
        cta_text='VIEW FULL RESULTS', cta_url=f'{base}/',
    )
    return send_email(to, f'SharpPicks Result \u2014 {side} {subject_icon} {result_label}', html)


# ── 11. Weekly Recap ──

def send_weekly_summary(to, first_name=None, stats=None):
    base = get_base_url()
    s = stats or {}
    wins = s.get('wins', 0)
    losses = s.get('losses', 0)
    picks_made = s.get('picks_made', 0)
    passes = s.get('passes', 0)
    pending = s.get('pending', 0)
    roi = s.get('roi', 0)
    total_record = s.get('total_record', '')
    units = s.get('units', 0)
    avg_edge = s.get('avg_edge', 0)
    season_units = s.get('season_units', 0)
    season_roi = s.get('season_roi', 0)
    clv_pct = s.get('clv_pct', 0)
    week_range = s.get('week_range', '')

    record_str = f'{wins}-{losses}'
    if pending:
        record_str += f' ({pending} pending)'

    roi_color = '#5A9E72' if roi >= 0 else '#CC3333'

    body = f'''
    {f'<p style="font-family:Arial,Helvetica,sans-serif;font-size:13px;color:#666666;margin:0 0 20px;">{week_range}</p>' if week_range else ''}
    <table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:0 0 8px;">
      <tr>
        <td style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#FFFFFF;padding:6px 0;">Record: <strong>{record_str}</strong></td>
        <td align="right" style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:{roi_color};padding:6px 0;">ROI: {roi:+.1f}%</td>
      </tr>
      <tr>
        <td style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#FFFFFF;padding:6px 0;">Units: {"+" if units >= 0 else ""}{units:.1f}u</td>
        <td align="right" style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#FFFFFF;padding:6px 0;">Avg Edge: +{avg_edge:.1f}%</td>
      </tr>
    </table>
    <hr style="border:none;border-top:1px solid #2A2A2A;margin:16px 0;">
    <table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:0 0 8px;">
      <tr>
        <td style="font-family:Arial,Helvetica,sans-serif;font-size:13px;color:#AAAAAA;padding:4px 0;">
          Season: {total_record}{f" &middot; CLV+: {clv_pct}%" if clv_pct else ""}
        </td>
      </tr>
    </table>
    <p style="font-family:Arial,Helvetica,sans-serif;font-size:13px;color:#AAAAAA;margin:8px 0 20px;">
      Days passed this week: {passes}
    </p>'''

    html = _base_template(
        'WEEKLY REPORT', body,
        cta_text='VIEW FULL REPORT', cta_url=f'{base}/',
        unsubscribe=True,
    )
    subj = f'SharpPicks Weekly \u2014 {record_str} \u00b7 {"+" if units >= 0 else ""}{units:.1f}u \u00b7 {roi:+.1f}% ROI' if picks_made > 0 else 'SharpPicks Weekly \u2014 All pass week'
    return send_email(to, subj, html, reply_to='evan@sharppicks.ai')


# ── 12. Founding Member Confirmation ──

def send_founding_member_email(to, member_number=None, total=100, joined_date=None):
    base = get_base_url()
    num = member_number or '—'
    joined = joined_date.strftime('%b %-d, %Y') if joined_date else ''

    body = f'''
    <p style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#AAAAAA;line-height:1.7;margin:0 0 16px;">
      Your founding member status has been confirmed.
    </p>
    <table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:0 0 24px;">
      <tr><td align="center" style="padding:20px;background-color:#1A1A1A;border-radius:6px;">
        <p style="font-family:'Courier New',Courier,monospace;font-size:28px;font-weight:bold;color:#FFFFFF;margin:0 0 8px;">
          #{num} of {total}
        </p>
        <p style="font-family:Arial,Helvetica,sans-serif;font-size:13px;color:#666666;margin:0;">
          Status: Founding Member{f" &middot; Joined: {joined}" if joined else ""}
        </p>
      </td></tr>
    </table>
    <p style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#AAAAAA;line-height:1.7;margin:0 0 16px;">
      Founding members receive priority access to all future features, including WNBA signals, player props, and advanced analytics.
    </p>
    <p style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#AAAAAA;line-height:1.7;margin:0 0 24px;">
      This status is permanent and non-transferable.
    </p>'''

    html = _base_template(
        'MEMBER STATUS', body,
        cta_text='ENTER MARKET VIEW', cta_url=f'{base}/',
    )
    return send_email(to, 'SharpPicks \u2014 Founding member status confirmed', html)


# ── 13. Daily Market Scan Complete (No Signal) ──

def send_no_signal_email(to, games_analyzed=0, edges_detected=0, efficiency=0):
    base = get_base_url()

    body = f'''
    <p style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#AAAAAA;line-height:1.7;margin:0 0 16px;">
      Today&rsquo;s market was analyzed. No edge exceeded the qualification threshold.
    </p>
    <p style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#5A9E72;font-style:italic;margin:0 0 24px;">
      Passing is a position.
    </p>
    <table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:0 0 24px;">
      <tr><td style="padding:16px;background-color:#1A1A1A;border-radius:6px;">
        <table cellpadding="0" cellspacing="0" border="0" width="100%">
          <tr><td style="font-family:'Courier New',Courier,monospace;font-size:15px;color:#FFFFFF;padding:4px 0;">Games analyzed: {games_analyzed}</td></tr>
          <tr><td style="font-family:'Courier New',Courier,monospace;font-size:15px;color:#FFFFFF;padding:4px 0;">Edges detected: {edges_detected}</td></tr>
          <tr><td style="font-family:'Courier New',Courier,monospace;font-size:15px;color:#FFFFFF;padding:4px 0;">Qualified signals: 0</td></tr>
          <tr><td style="font-family:'Courier New',Courier,monospace;font-size:15px;color:#FFFFFF;padding:4px 0;">Market efficiency: {efficiency:.0f}%</td></tr>
        </table>
      </td></tr>
    </table>'''

    html = _base_template(
        'MARKET SCAN', body,
        cta_text='VIEW MARKET REPORT', cta_url=f'{base}/',
        unsubscribe=True,
    )
    return send_email(to, 'SharpPicks \u2014 Market scan complete \u00b7 No qualifying signal', html)


# ── Legacy: Founder welcome (preserving for backward compat) ──

def send_welcome(to, first_name=None):
    name = first_name or "there"
    dashboard_url = get_base_url()

    attachments = []
    sig_b64 = _get_sig_b64()
    if sig_b64:
        attachments.append({
            "content": sig_b64,
            "filename": "evan-signature.png",
            "content_id": "evan-sig",
            "content_type": "image/png",
        })

    sig_src = 'cid:evan-sig' if sig_b64 else f'{get_base_url()}/evan-signature.png'

    html = f"""
    <div style="font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 520px; margin: 0 auto; padding: 20px 24px 48px; color: #e0e0e0; background-color: #0A0D14;">
      <div style="text-align: center; margin-bottom: 24px;">
        <img src="{dashboard_url}/images/crest.png" alt="" width="28" height="28" style="display:inline-block;vertical-align:middle;margin-right:12px;" /><!--
        --><span style="font-family:Arial,Helvetica,sans-serif;font-size:13px;font-weight:800;letter-spacing:0.3em;text-transform:uppercase;color:#FFFFFF;vertical-align:middle;">SHARP<span style="opacity:0.5;margin:0 0.35em;font-weight:500;letter-spacing:0.15em;">||</span>PICKS</span>
      </div>

      <p style="font-size: 15px; line-height: 1.9; color: #b8b8b8; margin-bottom: 24px; margin-top: 0;">Hi {name},</p>

      <p style="font-size: 15px; line-height: 1.9; color: #b8b8b8; margin-bottom: 24px;">Welcome to SharpPicks.</p>

      <p style="font-size: 15px; line-height: 1.9; color: #b8b8b8; margin-bottom: 24px;">Most people treat sports betting like a game of luck. We treat it like a market. By joining this community, you've chosen to move away from the noise and toward a data-driven, disciplined approach.</p>

      <p style="font-size: 15px; line-height: 1.9; color: #b8b8b8; margin-bottom: 24px;">Evan Cole here. I built this platform because I was tired of the "hype" culture. I wanted a tool that prioritized institutional-grade tracking and transparency over flashy promos.</p>

      <p style="font-size: 15px; line-height: 1.9; color: #ffffff; font-weight: 600; margin-bottom: 16px;">Here is how to get the most out of your first 24 hours:</p>

      <table style="width: 100%; border-collapse: collapse; margin-bottom: 28px;">
        <tr>
          <td style="padding: 14px 16px; border-bottom: 1px solid #1a1d28;">
            <span style="font-size: 14px; font-weight: 700; color: #5A9E72; margin-right: 10px;">1.</span>
            <span style="font-size: 15px; color: #ffffff; font-weight: 600;">Set Your Unit Size</span>
            <p style="font-size: 13px; color: #888; margin: 4px 0 0 22px; line-height: 1.6;">Discipline starts with bankroll management.</p>
          </td>
        </tr>
        <tr>
          <td style="padding: 14px 16px; border-bottom: 1px solid #1a1d28;">
            <span style="font-size: 14px; font-weight: 700; color: #5A9E72; margin-right: 10px;">2.</span>
            <span style="font-size: 15px; color: #ffffff; font-weight: 600;">Explore Today's Analysis</span>
            <p style="font-size: 13px; color: #888; margin: 4px 0 0 22px; line-height: 1.6;">See what the model found &#8212; or why it passed.</p>
          </td>
        </tr>
        <tr>
          <td style="padding: 14px 16px;">
            <span style="font-size: 14px; font-weight: 700; color: #5A9E72; margin-right: 10px;">3.</span>
            <span style="font-size: 15px; color: #ffffff; font-weight: 600;">Review the Public Record</span>
            <p style="font-size: 13px; color: #888; margin: 4px 0 0 22px; line-height: 1.6;">Every pick and pass tracked transparently &#8212; verified by data, not talk.</p>
          </td>
        </tr>
      </table>

      <div style="margin: 28px 0 28px 0; padding: 20px 24px; border-left: 3px solid #5A9E72; background-color: rgba(27, 122, 61, 0.04);">
        <div style="font-family: 'Courier New', monospace; font-size: 9px; font-weight: 700; letter-spacing: 2.5px; text-transform: uppercase; color: #5A9E72; margin-bottom: 14px;">Sharp Principle</div>
        <p style="font-family: Georgia, 'Times New Roman', serif; font-size: 19px; line-height: 1.55; color: #ffffff; font-weight: 500; font-style: italic; margin: 0;">The goal isn't just to win a bet; it's to build a sustainable edge.</p>
      </div>

      <div style="text-align: center; margin: 32px 0;">
        <a href="{dashboard_url}" style="display: inline-block; padding: 14px 36px; background-color: #5A9E72; color: #ffffff; text-decoration: none; border-radius: 6px; font-size: 14px; font-weight: bold; font-family: Arial, sans-serif; letter-spacing: 0.05em; text-transform: uppercase;">ENTER MARKET VIEW</a>
      </div>

      <p style="font-size: 15px; line-height: 1.9; color: #b8b8b8; margin-bottom: 32px;">If you have questions or feedback on the interface, reply directly to this email. I'm personally looking for ways to make our tools sharper for you.</p>

      <p style="font-size: 15px; line-height: 1.9; color: #b8b8b8; margin-bottom: 4px;">To the edge,</p>

      <div style="margin-bottom: 0; padding-bottom: 0;">
        <img src="{sig_src}" alt="Evan" style="height: 140px; width: auto; display: block; margin-left: -20px; margin-bottom: 0;" />
      </div>
      <table cellpadding="0" cellspacing="0" border="0"><tr>
        <td style="vertical-align: middle; padding-right: 12px;">
          <div style="width: 40px; height: 40px; border-radius: 50%; background: linear-gradient(135deg, rgba(27,122,61,0.2), rgba(27,122,61,0.15)); border: 1px solid rgba(27,122,61,0.3); text-align: center; line-height: 38px;">
            <span style="font-size: 15px; font-weight: 600; color: #5A9E72;">EC</span>
          </div>
        </td>
        <td style="vertical-align: middle;">
          <div style="font-size: 17px; color: #ffffff; font-weight: 600; font-family: 'Inter', -apple-system, sans-serif;">Evan Cole</div>
          <div style="font-size: 13px; color: #777; font-family: 'Inter', -apple-system, sans-serif; margin-top: 2px;">Founder, SharpPicks</div>
        </td>
      </tr></table>

      <hr style="border: none; border-top: 1px solid #2A2A2A; margin: 36px 0;">
      <p style="font-size: 12px; color: #444; text-align: center;">SharpPicks &mdash; Discipline is the product.</p>
      <p style="font-size: 12px; color: #444; text-align: center; margin-top: 4px;">support@sharppicks.ai</p>
    </div>
    """
    return send_email(
        to,
        "SharpPicks \u2014 Account active",
        html,
        reply_to="evan@sharppicks.ai",
        from_email=FOUNDER_EMAIL,
        attachments=attachments or None,
    )
