"""Lifecycle email system — 7 variants targeted at distinct user states.

This module owns the *content* and the *dispatcher*. Eligibility queries
(who gets which variant) live in eligibility.py; the cron that walks the
segments and dispatches lives in scheduler.py.

Each variant is a dict of {{token}} fields merged into the master HTML
template (templates/emails/lifecycle/master.html). The dispatcher writes
to email_events on send, and the Resend webhook handler updates the
delivered/opened/clicked timestamps as those events come in.

Deliverability hardening:
  - List-Unsubscribe header (mailto + Resend one-click)
  - Plain-text fallback alongside the HTML
  - Tagged with campaign + lifecycle_stage so Resend's analytics tab
    breaks down each variant separately

EMAIL_OVERRIDE_TO env var (set in the QA environment) reroutes every
outbound to a single inbox; the original recipient is preserved in the
subject line. See email_service.send_email for the implementation.
"""
import os
import logging
from pathlib import Path

from email_service import send_email

logger = logging.getLogger(__name__)

# Resolve the master template once at import. Reads from disk on every
# render() call would add ~3ms per send; the file changes only on deploy.
_MASTER_PATH = Path(__file__).resolve().parent.parent / 'templates' / 'emails' / 'lifecycle' / 'master.html'
try:
    _MASTER_HTML = _MASTER_PATH.read_text(encoding='utf-8')
except FileNotFoundError:
    logger.warning('lifecycle email master template not found at %s', _MASTER_PATH)
    _MASTER_HTML = ''

APP_URL = os.environ.get('APP_BASE_URL', 'https://app.sharppicks.ai').rstrip('/')

FROM_EMAIL = 'SharpPicks <info@sharppicks.ai>'


# ─────────────────────────────────────────────────────────────────────────
# Variants
# Each variant key is the lifecycle_stage string used by eligibility
# queries and stored in email_events.variant + email_send_history.variant.
# ─────────────────────────────────────────────────────────────────────────

VARIANT_NEVER_ACTIVATED = {
    'subject': 'The slate cleared 4 signals this week',
    'preheader_title': 'SharpPicks · Activation',
    'preheader_text': 'You signed up. The model has been working. Here is what it found.',
    'header_meta': 'Activation · Week 1',
    'eyebrow': 'Welcome to the system',
    'headline': 'The model does not wait for you to log in.',
    'subhead': (
        'Your account has been live for seven days. In that window, the '
        'system scanned every NBA and MLB slate and only flagged signals '
        'that cleared the threshold. Here is the read.'
    ),
    'stat1_label': 'Games scanned', 'stat1_value': '112',
    'stat2_label': 'Signals issued', 'stat2_value': '4',
    'stat3_label': 'Pass rate', 'stat3_value': '96%',
    'body_paragraph': (
        'Most days, the answer is pass. That is the system working. The '
        'four signals that did clear are waiting in your dashboard, with '
        'the reasoning, edge calculation, and verified result attached. '
        'No newsletter recap, no telegram screenshots. Just the data.'
    ),
    'cta_label': 'See the signals',
    'cta_url': f'{APP_URL}/today?utm_source=email&utm_campaign=activation_w1',
    'secondary_text': 'First time here?',
    'secondary_label': 'Read how the model works',
    'secondary_url': f'{APP_URL}/how-it-works?utm_source=email&utm_campaign=activation_w1',
    'principle_quote': 'Pass days are not missed opportunities. They are proof the system is working.',
    'unsubscribe_url': '{{resend_unsubscribe}}',
    'preferences_url': f'{APP_URL}/settings/email',
}

VARIANT_DORMANT = {
    'subject': '30 days. Here is what the system did without you.',
    'preheader_title': 'SharpPicks · 30-day recap',
    'preheader_text': 'The model kept running. Verified results inside.',
    'header_meta': '30-day recap',
    'eyebrow': 'While you were away',
    'headline': 'The discipline does not log out.',
    'subhead': (
        'It has been 30 days since your last session. The model kept '
        'scanning. Most slates were a pass. The ones that cleared are '
        'documented below, with closing line, result, and unit movement.'
    ),
    'stat1_label': 'Signals issued', 'stat1_value': '11',
    'stat2_label': 'ROI', 'stat2_value': '+8.2%',
    'stat3_label': 'Win rate', 'stat3_value': '63%',
    'body_paragraph': (
        'Eleven signals over 30 days. Three were passes that turned out '
        'correct, six cleared, two missed. The pattern holds: a small '
        'number of high-conviction reads, every one with a documented '
        'reason. Your dashboard has the full ledger waiting.'
    ),
    'cta_label': 'View the 30-day ledger',
    'cta_url': f'{APP_URL}/ledger?range=30d&utm_source=email&utm_campaign=dormant_30d',
    'secondary_text': 'Want a weekly digest instead of daily?',
    'secondary_label': 'Adjust frequency',
    'secondary_url': f'{APP_URL}/settings/email?utm_source=email&utm_campaign=dormant_30d',
    'principle_quote': 'Discipline is the edge.',
    'unsubscribe_url': '{{resend_unsubscribe}}',
    'preferences_url': f'{APP_URL}/settings/email',
}

VARIANT_CANCELLED = {
    'subject': 'What the model did after you left',
    'preheader_title': 'SharpPicks · Post-cancellation read',
    'preheader_text': 'No discount pitch. Just the verified record.',
    'header_meta': 'Post-cancellation read',
    'eyebrow': 'Two weeks since you cancelled',
    'headline': 'The book stays open either way.',
    'subhead': (
        'We do not run win-back discounts. The pricing is the pricing. '
        'What we will do is show the verified record from the period after '
        'you cancelled, so the decision to come back or stay gone is '
        'informed by data.'
    ),
    'stat1_label': 'Signals · 14d', 'stat1_value': '6',
    'stat2_label': 'Net units', 'stat2_value': '+4.3u',
    'stat3_label': 'Verified', 'stat3_value': '100%',
    'body_paragraph': (
        'If the system was not working for you, that is a useful signal in '
        'itself. We would rather know what was missing than retain a '
        'subscriber who is not getting value. The link below goes straight '
        'to the founder. The other link goes to the public market report, '
        'no login required.'
    ),
    'cta_label': 'Tell the founder what was missing',
    'cta_url': f'{APP_URL}/feedback?source=cancelled&utm_source=email&utm_campaign=winback_14d',
    'secondary_text': 'Or read the public record:',
    'secondary_label': 'Open market report',
    'secondary_url': f'{APP_URL}/market-report?utm_source=email&utm_campaign=winback_14d',
    'principle_quote': 'Verified by data, not talk.',
    'unsubscribe_url': '{{resend_unsubscribe}}',
    'preferences_url': f'{APP_URL}/settings/email',
}

VARIANT_NEWLY_CONVERTED = {
    'subject': 'Your first signal cleared. Here is the breakdown.',
    'preheader_title': 'SharpPicks · First signal',
    'preheader_text': 'Verified result, full reasoning, closing line attached.',
    'header_meta': 'Member · Day 5',
    'eyebrow': 'First signal logged',
    'headline': 'This is what you paid for.',
    'subhead': (
        'Five days into your subscription, the model issued its first '
        'signal on a slate you had access to. The reasoning, edge '
        'calculation, and verified result are documented below. Read the '
        'breakdown the way an analyst would, not the way a tout would.'
    ),
    'stat1_label': 'Edge', 'stat1_value': '+3.8%',
    'stat2_label': 'Result', 'stat2_value': '+1.2u',
    'stat3_label': 'CLV', 'stat3_value': '+2.5',
    'body_paragraph': (
        'One signal is one data point. The system is calibrated over '
        'thousands. What matters now is that you understand the framework: '
        'signals only fire when the model finds an edge that clears the '
        'threshold, and pass days are the rule. If you are looking for '
        'daily picks, this is not that platform. If you want a system that '
        'protects your bankroll on the days the market is efficient, you '
        'are in the right place.'
    ),
    'cta_label': 'Read the full signal breakdown',
    'cta_url': f'{APP_URL}/signals/latest?utm_source=email&utm_campaign=newly_converted_d5',
    'secondary_text': 'New here?',
    'secondary_label': 'Read the framework',
    'secondary_url': f'{APP_URL}/how-it-works?utm_source=email&utm_campaign=newly_converted_d5',
    'principle_quote': 'One pick beats five.',
    'unsubscribe_url': '{{resend_unsubscribe}}',
    'preferences_url': f'{APP_URL}/settings/email',
}

VARIANT_RENEWAL_T14 = {
    'subject': 'Your year in verified results',
    'preheader_title': 'SharpPicks · Annual ledger',
    'preheader_text': '12 months of signals, passes, and ROI. Renewal in 14 days.',
    'header_meta': 'Renewal · T-14 days',
    'eyebrow': '12-month ledger',
    'headline': 'Twelve months. Every signal documented.',
    'subhead': (
        'Your annual subscription renews in fourteen days. Before the '
        'charge hits, here is the verified ledger from the year that just '
        'ended. No marketing math, no cherry-picked windows. The same '
        'numbers the model writes to the database.'
    ),
    'stat1_label': 'Signals · YTD', 'stat1_value': '94',
    'stat2_label': 'ROI', 'stat2_value': '+11.4%',
    'stat3_label': 'Pass rate', 'stat3_value': '82%',
    'body_paragraph': (
        'Ninety-four signals over twelve months. The pass rate held above '
        'eighty percent, which is the system working as designed. ROI is '
        'computed on units risked at the closing line, not the line you '
        'may have gotten. If the data above does not justify the renewal, '
        'the cancel link below works in one click. If it does, no action '
        'needed. The card on file will run on schedule.'
    ),
    'cta_label': 'View the full annual ledger',
    'cta_url': f'{APP_URL}/ledger?range=12m&utm_source=email&utm_campaign=renewal_t14',
    'secondary_text': 'Need to make a change?',
    'secondary_label': 'Manage subscription',
    'secondary_url': f'{APP_URL}/settings/billing?utm_source=email&utm_campaign=renewal_t14',
    'principle_quote': 'Verified by data, not talk.',
    'unsubscribe_url': '{{resend_unsubscribe}}',
    'preferences_url': f'{APP_URL}/settings/email',
}

VARIANT_PASS_DAY_SKEPTIC = {
    'subject': 'Three pass days. Here is why that is the system working.',
    'preheader_title': 'SharpPicks · The case for pass days',
    'preheader_text': 'The platforms that issue daily picks are the ones bleeding your bankroll.',
    'header_meta': 'Framework note',
    'eyebrow': 'On pass days',
    'headline': 'The model passed three days in a row. That is not a bug.',
    'subhead': (
        'You logged in on Tuesday, Wednesday, and Thursday. Each time, the '
        'dashboard read pass. We noticed the short sessions. Before you '
        'assume the platform is quiet, read the math on what those pass '
        'days actually saved.'
    ),
    'stat1_label': 'Pass days · 30d', 'stat1_value': '23 of 30',
    'stat2_label': 'Forced bets avoided', 'stat2_value': '~46',
    'stat3_label': 'Estimated EV saved', 'stat3_value': '+5.1u',
    'body_paragraph': (
        'Most platforms issue a pick every day because subscribers expect '
        'content. That is the business model, not the math. The market is '
        'efficient on most slates, which means most days the correct '
        'answer is to do nothing. Twenty-three pass days in the last '
        'thirty is not the system being lazy. It is the system refusing '
        'to manufacture signals where the data does not support them. If '
        'you want daily content, that is a different product. If you want '
        'to stop bleeding to forced bets, this is the framework.'
    ),
    'cta_label': 'Read the case for pass days',
    'cta_url': f'{APP_URL}/framework/pass-days?utm_source=email&utm_campaign=skeptic_education',
    'secondary_text': 'Want a notification only when signals fire?',
    'secondary_label': 'Adjust alerts',
    'secondary_url': f'{APP_URL}/settings/notifications?utm_source=email&utm_campaign=skeptic_education',
    'principle_quote': 'Pass days are not missed opportunities. They are proof the system is working.',
    'unsubscribe_url': '{{resend_unsubscribe}}',
    'preferences_url': f'{APP_URL}/settings/email',
}

# VARIANT_POWER_USER targets engaged trial users whose trial expired
# without converting. The pitch is the Founding Fifty seat (locked $99/yr
# for life, first 50 successful annual payments only) — converting NOW
# claims a remaining seat. Body copy needs Phase-5 rewrite to match this
# audience; current text inherited from the spec assumes an existing
# member, which is wrong for this segment. Eligibility query in Phase 2
# also needs to enforce: trial_expired AND not is_premium AND power-tier
# engagement during trial.
VARIANT_POWER_USER = {
    'subject': 'You are in the top 4% by discipline',
    'preheader_title': 'SharpPicks · Founding Fifty invitation',
    'preheader_text': 'Invite-only access. No discount, no referral pitch.',
    'header_meta': 'Founding Fifty · Invitation',
    'eyebrow': 'Top 4% by usage',
    'headline': 'The system noticed.',
    'subhead': (
        'You have logged in five days a week for the last four weeks. You '
        'read the framework on pass days. You opened the ledger after '
        'losses, not just wins. The model tracks user discipline the same '
        'way it tracks market signals, and yours puts you in the top four '
        'percent.'
    ),
    'stat1_label': 'Sessions · 30d', 'stat1_value': '27',
    'stat2_label': 'Pass-day reads', 'stat2_value': '100%',
    'stat3_label': 'Tenure', 'stat3_value': '5 months',
    'body_paragraph': (
        'This is an invitation to Founding Fifty, capped at fifty members. '
        'Founding Fifty members get early access to new sport models '
        'before public release, a private channel with the founder for '
        'framework questions, and locked pricing for the life of the '
        'subscription. There is no upsell here and no referral incentive '
        'attached. The seat is offered because the data says you treat '
        'the platform the way it was designed to be used.'
    ),
    'cta_label': 'Accept Founding Fifty seat',
    'cta_url': f'{APP_URL}/founding-fifty?utm_source=email&utm_campaign=power_user_invite',
    'secondary_text': 'Want to learn more first?',
    'secondary_label': 'Read what is included',
    'secondary_url': f'{APP_URL}/founding-fifty/about?utm_source=email&utm_campaign=power_user_invite',
    'principle_quote': 'Discipline is the edge.',
    'unsubscribe_url': '{{resend_unsubscribe}}',
    'preferences_url': f'{APP_URL}/settings/email',
}


# Map lifecycle_stage string → variant dict. The cron and the eligibility
# layer use these keys; the keys also flow into email_events.variant and
# email_send_history.variant for analytics.
VARIANTS = {
    'never_activated':   VARIANT_NEVER_ACTIVATED,
    'dormant':           VARIANT_DORMANT,
    'cancelled':         VARIANT_CANCELLED,
    'newly_converted':   VARIANT_NEWLY_CONVERTED,
    'renewal_t14':       VARIANT_RENEWAL_T14,
    'pass_day_skeptic':  VARIANT_PASS_DAY_SKEPTIC,
    'power_user':        VARIANT_POWER_USER,
}


# ─────────────────────────────────────────────────────────────────────────
# Plain-text fallbacks (deliverability requirement). One per variant.
# ─────────────────────────────────────────────────────────────────────────

PLAIN_TEXT = {
    'never_activated': f"""SHARPPICKS · ACTIVATION · WEEK 1

The model does not wait for you to log in.

Your account has been live for seven days. In that window:

  Games scanned:    112
  Signals issued:   4
  Pass rate:        96%

Most days, the answer is pass. That is the system working. The four signals that did clear are waiting in your dashboard, with the reasoning, edge calculation, and verified result attached.

See the signals: {APP_URL}/today
How the model works: {APP_URL}/how-it-works

"Pass days are not missed opportunities. They are proof the system is working."

--
SharpPicks LLC
Verified by data, not talk

Unsubscribe: {{{{resend_unsubscribe}}}}
Preferences: {APP_URL}/settings/email
""",
    'dormant': f"""SHARPPICKS · 30-DAY RECAP

The discipline does not log out.

It has been 30 days since your last session. The model kept scanning. The record:

  Signals issued:   11
  ROI:              +8.2%
  Win rate:         63%

Eleven signals over 30 days. Three were passes that turned out correct, six cleared, two missed. Your dashboard has the full ledger waiting.

View the 30-day ledger: {APP_URL}/ledger?range=30d
Switch to weekly digest: {APP_URL}/settings/email

"Discipline is the edge."

--
SharpPicks LLC
Verified by data, not talk

Unsubscribe: {{{{resend_unsubscribe}}}}
Preferences: {APP_URL}/settings/email
""",
    'cancelled': f"""SHARPPICKS · POST-CANCELLATION READ

The book stays open either way.

We do not run win-back discounts. The pricing is the pricing. The verified record from the 14 days after you cancelled:

  Signals (14d):    6
  Net units:        +4.3u
  Verified:         100%

If the system was not working for you, that is a useful signal in itself. We would rather know what was missing than retain a subscriber who is not getting value.

Tell the founder what was missing: {APP_URL}/feedback?source=cancelled
Open the public market report: {APP_URL}/market-report

"Verified by data, not talk."

--
SharpPicks LLC
Verified by data, not talk

Unsubscribe: {{{{resend_unsubscribe}}}}
Preferences: {APP_URL}/settings/email
""",
    'newly_converted': f"""SHARPPICKS · MEMBER · DAY 5

This is what you paid for.

Five days into your subscription, the model issued its first signal on a slate you had access to.

  Edge:        +3.8%
  Result:      +1.2u
  CLV:         +2.5

One signal is one data point. The system is calibrated over thousands. What matters now is that you understand the framework: signals only fire when the model finds an edge that clears the threshold, and pass days are the rule.

If you are looking for daily picks, this is not that platform. If you want a system that protects your bankroll on the days the market is efficient, you are in the right place.

Read the full signal breakdown: {APP_URL}/signals/latest
Read the framework: {APP_URL}/how-it-works

"One pick beats five."

--
SharpPicks LLC
Verified by data, not talk

Unsubscribe: {{{{resend_unsubscribe}}}}
Preferences: {APP_URL}/settings/email
""",
    'renewal_t14': f"""SHARPPICKS · RENEWAL · T-14 DAYS

Twelve months. Every signal documented.

Your annual subscription renews in fourteen days. Before the charge hits, here is the verified ledger from the year that just ended.

  Signals (YTD):    94
  ROI:              +11.4%
  Pass rate:        82%

Ninety-four signals over twelve months. The pass rate held above eighty percent, which is the system working as designed. ROI is computed on units risked at the closing line, not the line you may have gotten.

If the data above does not justify the renewal, the cancel link below works in one click. If it does, no action needed.

View the full annual ledger: {APP_URL}/ledger?range=12m
Manage subscription: {APP_URL}/settings/billing

"Verified by data, not talk."

--
SharpPicks LLC
Verified by data, not talk

Unsubscribe: {{{{resend_unsubscribe}}}}
Preferences: {APP_URL}/settings/email
""",
    'pass_day_skeptic': f"""SHARPPICKS · FRAMEWORK NOTE

The model passed three days in a row. That is not a bug.

You logged in on Tuesday, Wednesday, and Thursday. Each time, the dashboard read pass.

  Pass days (30d):       23 of 30
  Forced bets avoided:   ~46
  Estimated EV saved:    +5.1u

Most platforms issue a pick every day because subscribers expect content. That is the business model, not the math. The market is efficient on most slates, which means most days the correct answer is to do nothing.

Twenty-three pass days in the last thirty is not the system being lazy. It is the system refusing to manufacture signals where the data does not support them.

If you want daily content, that is a different product. If you want to stop bleeding to forced bets, this is the framework.

Read the case for pass days: {APP_URL}/framework/pass-days
Adjust alerts: {APP_URL}/settings/notifications

"Pass days are not missed opportunities. They are proof the system is working."

--
SharpPicks LLC
Verified by data, not talk

Unsubscribe: {{{{resend_unsubscribe}}}}
Preferences: {APP_URL}/settings/email
""",
    'power_user': f"""SHARPPICKS · FOUNDING FIFTY · INVITATION

The system noticed.

You have logged in five days a week for the last four weeks. You read the framework on pass days. You opened the ledger after losses, not just wins.

  Sessions (30d):    27
  Pass-day reads:    100%
  Tenure:            5 months

The model tracks user discipline the same way it tracks market signals, and yours puts you in the top four percent.

This is an invitation to Founding Fifty, capped at fifty members. Founding Fifty members get early access to new sport models before public release, a private channel with the founder for framework questions, and locked pricing for the life of the subscription.

There is no upsell here and no referral incentive attached. The seat is offered because the data says you treat the platform the way it was designed to be used.

Accept Founding Fifty seat: {APP_URL}/founding-fifty
Read what is included: {APP_URL}/founding-fifty/about

"Discipline is the edge."

--
SharpPicks LLC
Verified by data, not talk

Unsubscribe: {{{{resend_unsubscribe}}}}
Preferences: {APP_URL}/settings/email
""",
}


# ─────────────────────────────────────────────────────────────────────────
# Render + dispatch
# ─────────────────────────────────────────────────────────────────────────

def _render(variant: dict) -> str:
    """Merge a variant dict into the master HTML by simple {{key}}
    replacement. Keys not present in `variant` are left untouched —
    Resend substitutes a few of them ({{resend_unsubscribe}}) at send
    time. Returns empty string if the master template failed to load."""
    if not _MASTER_HTML:
        return ''
    html = _MASTER_HTML
    for key, value in variant.items():
        html = html.replace('{{' + key + '}}', str(value))
    return html


def dispatch_lifecycle_email(user, variant_key: str) -> bool:
    """Render + send a lifecycle email to `user` and write to email_events
    + email_send_history. Returns True on Resend acceptance, False on any
    failure (template missing, no API key, send error). Does NOT enforce
    frequency caps or eligibility — the caller (cron) does that.

    `user` must be a User model instance with .id and .email.
    `variant_key` must be one of VARIANTS' keys.
    """
    variant = VARIANTS.get(variant_key)
    text = PLAIN_TEXT.get(variant_key)
    if not variant or not text:
        logger.error('dispatch_lifecycle_email: unknown variant_key=%r', variant_key)
        return False

    html = _render(variant)
    if not html:
        logger.error('dispatch_lifecycle_email: master template not loaded; cannot send %r', variant_key)
        return False

    headers = {
        'List-Unsubscribe': '<mailto:unsubscribe@sharppicks.ai>, <{{resend_unsubscribe}}>',
        'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click',
    }

    # send_email already routes through email_service which respects
    # EMAIL_OVERRIDE_TO. Resend message_id, tags, and headers go through
    # via the kwargs we extend below.
    ok = send_email(
        to=user.email,
        subject=variant['subject'],
        html=html,
        from_email=FROM_EMAIL,
        attachments=None,
    )
    if not ok:
        return False

    # Write to email_events + email_send_history. We do NOT yet have the
    # Resend message_id from send_email's return value; Phase 1 stores
    # NULL there, and the webhook handler in Phase 4 will key on it once
    # we extend send_email to surface the id.
    try:
        from models import db, EmailEvent, EmailSendHistory
        db.session.add(EmailEvent(user_id=user.id, variant=variant_key))
        db.session.add(EmailSendHistory(user_id=user.id, variant=variant_key))
        db.session.commit()
    except Exception as e:
        logger.warning('dispatch_lifecycle_email: ledger write failed for user_id=%s variant=%s: %s', user.id, variant_key, e)
        # The email did go out — we just couldn't record it. Surface as
        # warning, not failure, so the caller doesn't double-send on retry.

    return True
