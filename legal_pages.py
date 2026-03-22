from flask import Blueprint, Response

legal_bp = Blueprint('legal', __name__)

LEGAL_STYLE = """
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    background: #0A0D14; color: #E2E8F0;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    line-height: 1.7; padding: 0;
  }
  .legal-wrap {
    max-width: 680px; margin: 0 auto;
    padding: 40px 24px 80px;
  }
  .legal-back {
    display: inline-flex; align-items: center; gap: 6px;
    color: #64748B; font-size: 13px; text-decoration: none;
    margin-bottom: 32px; font-weight: 500;
  }
  .legal-back:hover { color: #94A3B8; }
  .legal-badge {
    display: inline-block; font-size: 10px; font-weight: 700;
    letter-spacing: 2px; text-transform: uppercase;
    color: #64748B; background: rgba(100,116,139,0.1);
    padding: 4px 10px; border-radius: 4px; margin-bottom: 12px;
  }
  h1 {
    font-family: 'IBM Plex Serif', Georgia, serif;
    font-size: 28px; font-weight: 700; color: #F8FAFC;
    margin-bottom: 8px; line-height: 1.3;
  }
  .legal-updated {
    font-size: 13px; color: #64748B; margin-bottom: 36px;
  }
  h2 {
    font-family: 'IBM Plex Serif', Georgia, serif;
    font-size: 20px; font-weight: 600; color: #F8FAFC;
    margin: 36px 0 14px; padding-top: 12px;
    border-top: 1px solid rgba(100,116,139,0.15);
  }
  h2:first-of-type { border-top: none; padding-top: 0; }
  p { margin-bottom: 16px; font-size: 15px; color: #CBD5E1; }
  ul {
    margin: 0 0 16px 0; padding-left: 20px;
  }
  li {
    font-size: 15px; color: #CBD5E1; margin-bottom: 8px;
    line-height: 1.6;
  }
  .callout {
    background: rgba(79,134,247,0.06);
    border-left: 3px solid #4F86F7;
    padding: 16px 20px; border-radius: 0 10px 10px 0;
    margin: 20px 0; font-size: 14px; color: #94A3B8;
    line-height: 1.7;
  }
  .callout-warn {
    background: rgba(245,158,11,0.06);
    border-left: 3px solid #F59E0B;
  }
  .callout-green {
    background: rgba(52,211,153,0.06);
    border-left: 3px solid #34D399;
  }
  a { color: #4F86F7; text-decoration: none; }
  a:hover { text-decoration: underline; }
  .legal-nav {
    margin-top: 48px; padding-top: 24px;
    border-top: 1px solid rgba(100,116,139,0.15);
  }
  .legal-nav-title {
    font-size: 11px; font-weight: 600; color: #64748B;
    text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px;
  }
  .legal-nav a {
    display: block; padding: 10px 0; font-size: 14px;
    color: #94A3B8; text-decoration: none;
    border-bottom: 1px solid rgba(100,116,139,0.08);
  }
  .legal-nav a:hover { color: #4F86F7; }
  .legal-nav a.active { color: #4F86F7; font-weight: 600; }
</style>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Serif:wght@400;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
"""

def legal_nav(active):
    pages = [
        ('terms', 'Terms of Service'),
        ('privacy', 'Privacy Policy'),
        ('refund', 'Refund Policy'),
        ('responsible-gaming', 'Sports Betting Legal Disclosure'),
        ('disclaimer', 'Founding Members'),
    ]
    links = ''.join(
        f'<a href="/legal/{slug}" class="{"active" if slug == active else ""}">{label}</a>'
        for slug, label in pages
    )
    return f'<div class="legal-nav"><div class="legal-nav-title">All Policies</div>{links}</div>'

def legal_page(title, active, body):
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — SharpPicks</title>
{LEGAL_STYLE}
</head>
<body>
<div class="legal-wrap">
  <a href="/" class="legal-back">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
    Back to SharpPicks
  </a>
  <div class="legal-badge">Legal</div>
  <h1>{title}</h1>
  <div class="legal-updated">Last updated: February 7, 2026</div>
  {body}
  {legal_nav(active)}
  <p style="margin-top:32px;font-size:11px;color:#475569;text-align:center;">
    &copy; 2026 SharpPicks. All rights reserved.
  </p>
</div>
</body>
</html>"""
    return Response(html, mimetype='text/html')


@legal_bp.route('/legal/terms')
def terms():
    body = """
  <h2>What SharpPicks Is</h2>
  <p>SharpPicks is a statistical analysis and information product. We analyze publicly available sports data and publish the results of that analysis to subscribers. That is the full extent of what we do.</p>
  <div class="callout">SharpPicks does not accept wagers, facilitate betting, operate as a sportsbook, or provide financial advice. We do not direct, instruct, or pressure users to place any bet.</div>

  <h2>What SharpPicks Is Not</h2>
  <p>SharpPicks does not provide betting advice, wagering recommendations, or guaranteed outcomes. The analysis published through our product reflects statistical probabilities, not certainties. No claim of future performance is made or implied.</p>
  <p>The terms "pick," "edge," and "qualified opportunity" as used in SharpPicks refer to the output of a statistical model, not instructions to act. All decisions to place, modify, or refrain from placing a wager are made solely by the user.</p>

  <h2>User Responsibility</h2>
  <p>By using SharpPicks, you acknowledge that:</p>
  <ul>
    <li>You are solely responsible for any wagering decisions you make</li>
    <li>You are solely responsible for understanding and complying with the laws of your jurisdiction</li>
    <li>You will not hold SharpPicks liable for betting losses or outcomes</li>
    <li>You understand that past performance does not guarantee future results</li>
    <li>You are of legal age in your jurisdiction to access sports analysis content</li>
  </ul>

  <h2>Jurisdiction</h2>
  <p>Sports betting legality varies by state, territory, and country. SharpPicks does not verify a user's eligibility to place bets and makes no representation that sports betting is legal in any particular jurisdiction. The availability of SharpPicks analysis does not imply the legality of sports betting in your location.</p>

  <h2>Subscription and Billing</h2>
  <p>SharpPicks offers a 14-day free trial for all new subscribers. After the trial period, your selected plan will bill automatically unless cancelled. Subscriptions renew automatically at the end of each billing period (monthly or annually) unless cancelled before the renewal date.</p>
  <p>You may cancel your subscription at any time. Cancellation takes effect at the end of the current billing period. No partial refunds are issued for unused portions of a billing period, except as described in the Refund Policy.</p>

  <h2>Founding Member Pricing</h2>
  <p>SharpPicks offers a founding member rate to the first 500 paid subscribers. The founding rate is locked in for the duration of an active, uninterrupted subscription. If a founding member cancels their subscription, the founding rate cannot be restored upon resubscription.</p>

  <h2>Content and Intellectual Property</h2>
  <p>All analysis, picks, model outputs, and editorial content published through SharpPicks are the intellectual property of SharpPicks. Users may not redistribute, resell, or publicly share Pro-tier content without written permission. The public record page is freely accessible and may be referenced or linked.</p>

  <h2>Limitation of Liability</h2>
  <p>SharpPicks provides information on an "as is" basis. We do not guarantee the accuracy, completeness, or reliability of any analysis. SharpPicks is not liable for any direct, indirect, incidental, or consequential damages arising from the use of our product, including but not limited to financial losses from wagering activity.</p>

  <h2>Modifications</h2>
  <p>We may update these Terms from time to time. Material changes will be communicated via email or in-app notification at least 14 days before they take effect. Continued use of SharpPicks after changes take effect constitutes acceptance of the updated Terms.</p>
"""
    return legal_page('Terms of Service', 'terms', body)


@legal_bp.route('/legal/privacy')
def privacy():
    body = """
  <h2>What We Collect</h2>
  <p>SharpPicks collects only the data necessary to operate the product and improve your experience:</p>
  <ul>
    <li><strong>Account information:</strong> Email address, password (hashed), display name</li>
    <li><strong>Subscription data:</strong> Plan type, billing status, founding member status</li>
    <li><strong>Usage analytics:</strong> App opens, feature interactions, screen views (anonymized)</li>
    <li><strong>Pick tracking inputs:</strong> If you enter a wager amount or outcome, that data is stored to your account</li>
    <li><strong>Device data:</strong> OS version, app version, crash logs (anonymized)</li>
  </ul>

  <h2>What We Do Not Collect</h2>
  <ul>
    <li>Sportsbook account information</li>
    <li>Betting history from third-party platforms</li>
    <li>Financial account details (payments are processed by a third-party provider)</li>
    <li>Location data beyond general region for timezone purposes</li>
  </ul>

  <h2>How We Use Your Data</h2>
  <p>We use collected data to:</p>
  <ul>
    <li>Operate your account and deliver the product</li>
    <li>Process subscription payments through our payment provider</li>
    <li>Send product notifications you have opted into</li>
    <li>Improve the product through anonymized usage analytics</li>
    <li>Communicate important account or policy changes</li>
  </ul>

  <div class="callout-green callout">We do not sell your personal data. We do not share your data with sportsbooks. We do not use your betting behavior for advertising targeting. We do not serve ads in SharpPicks.</div>

  <h2>Third-Party Services</h2>
  <p>SharpPicks uses the following categories of third-party services:</p>
  <ul>
    <li><strong>Payment processing:</strong> Subscription billing is handled by a PCI-compliant payment processor. We do not store credit card numbers.</li>
    <li><strong>Analytics:</strong> Anonymized usage analytics to understand product engagement. No personally identifiable information is shared.</li>
    <li><strong>Infrastructure:</strong> Cloud hosting and database services with encryption at rest and in transit.</li>
  </ul>

  <h2>Data Retention and Deletion</h2>
  <p>Account data is retained for the duration of your subscription and for 90 days after cancellation to allow for reactivation. After 90 days, account data is permanently deleted unless a longer retention period is required by law.</p>
  <p>You may request immediate deletion of your data at any time by contacting support. We will process deletion requests within 30 days.</p>

  <h2>Your Rights</h2>
  <p>You have the right to:</p>
  <ul>
    <li>Access the personal data we hold about you</li>
    <li>Request correction of inaccurate data</li>
    <li>Request deletion of your data</li>
    <li>Export your pick tracking history</li>
    <li>Opt out of non-essential communications</li>
  </ul>
  <p>To exercise any of these rights, contact us at the email provided in your account settings.</p>
"""
    return legal_page('Privacy Policy', 'privacy', body)


@legal_bp.route('/legal/refund')
def refund():
    body = """
  <h2>Free Trial</h2>
  <p>All new subscribers receive a 14-day free trial with full Pro access. No payment is charged during the trial. You may cancel at any time during the trial without charge.</p>

  <h2>Monthly Subscriptions</h2>
  <p>Monthly subscriptions are non-refundable once the billing period has begun. If you cancel, you retain access through the end of the current billing period.</p>

  <h2>Annual Subscriptions</h2>
  <p>Annual subscriptions may be refunded within 7 days of the initial purchase or renewal if no meaningful product use has occurred during that period. After 7 days, annual subscriptions are non-refundable. If you cancel, you retain access through the end of the annual billing period.</p>

  <div class="callout callout-warn">Refunds are not issued based on betting outcomes, pick frequency, or the number of pass days. The SharpPicks model is designed to be selective. Extended periods without a published pick are a normal and expected part of the product. By subscribing, you acknowledge that pass days are part of the product's value, not an absence of service.</div>

  <h2>Founding Member Rate</h2>
  <p>If you hold a founding member rate and cancel your subscription, the founding rate cannot be restored. If you resubscribe after cancellation, the standard rate at the time of resubscription will apply. This is stated clearly during the cancellation flow.</p>

  <h2>How to Request a Refund</h2>
  <p>Eligible refund requests can be submitted through your account settings or by contacting support. Refunds are processed within 10 business days to the original payment method.</p>
"""
    return legal_page('Refund Policy', 'refund', body)


@legal_bp.route('/legal/responsible-gaming')
def responsible_gaming():
    body = """
  <h2>Legal Status Varies by Jurisdiction</h2>
  <p>Sports betting is regulated differently across states, territories, and countries. The legality of placing a wager depends on your jurisdiction. SharpPicks does not verify, monitor, or enforce compliance with local betting laws.</p>

  <h2>SharpPicks Is Not a Sportsbook</h2>
  <p>SharpPicks does not accept wagers, process bets, hold funds, or facilitate any form of gambling. We are a statistical analysis product. Our content is informational in nature and does not constitute an offer, solicitation, or encouragement to place a wager.</p>

  <h2>User Responsibility</h2>
  <p>You are solely responsible for understanding and complying with the laws of your jurisdiction regarding sports betting. The availability of SharpPicks analysis in your location does not imply that sports betting is legal where you are.</p>

  <h2>Problem Gambling Resources</h2>
  <p>If you or someone you know is struggling with gambling, help is available:</p>
  <ul>
    <li><strong>National Council on Problem Gambling:</strong> 1-800-522-4700</li>
    <li><strong>NCPG Text Line:</strong> Text "HELP" to 233-4357</li>
    <li><strong>NCPG Chat:</strong> <a href="https://www.ncpgambling.org/chat" target="_blank" rel="noopener">ncpgambling.org/chat</a></li>
  </ul>
  <div class="callout callout-green">SharpPicks is designed to reduce impulsive betting behavior, not encourage it. If you find that our product or sports betting in general is causing you distress, we encourage you to seek support and to cancel your subscription.</div>

  <h2>Age Requirement</h2>
  <p>SharpPicks is intended for users who are at least 18 years of age, or the legal age for accessing sports analysis content in their jurisdiction, whichever is greater.</p>
"""
    return legal_page('Sports Betting Legal Disclosure', 'responsible-gaming', body)


@legal_bp.route('/legal/founding-members')
def founding_members():
    body = """
  <h2>Definition</h2>
  <p>"Founding member" refers to one of the first 500 paid Pro subscribers to SharpPicks, determined by the timestamp of successful initial payment (not trial start). Founding member status is assigned sequentially and cannot be transferred, purchased separately, or retroactively applied.</p>

  <h2>Founding Rate</h2>
  <p>Founding members receive the founding annual rate of $99/year. This rate is locked in for the duration of an active, continuous subscription. "Active and continuous" means the subscription has not been cancelled, lapsed, or interrupted.</p>
  <div class="callout callout-warn">If you cancel a founding rate subscription, the founding rate cannot be restored. If you resubscribe after cancellation, the standard rate at the time of resubscription will apply. This policy exists to keep the founding rate honest — it rewards commitment, not re-signups.</div>

  <h2>What Founding Members Receive</h2>
  <ul>
    <li>Founding rate of $99/year (locked while subscribed)</li>
    <li>Founding Member badge visible in account settings</li>
    <li>Same product access as all Pro subscribers — no extra picks, no special treatment</li>
  </ul>
  <p>Founding member status is a pricing distinction, not a product distinction. All Pro subscribers receive identical analysis, features, and access regardless of when they subscribed.</p>

  <h2>When Founding Ends</h2>
  <p>The founding member rate is available to the first 500 paid subscribers. Once 500 founding spots are filled, the founding rate is no longer available. The counter is not extended, reopened, or reset. After 500 founding members, the standard annual rate of $149/year applies to all new subscribers.</p>

  <h2>Tracking</h2>
  <p>The current founding member count is displayed publicly in the app. Your founding member number is shown in your account settings. These numbers are final and cannot be changed.</p>
"""
    return legal_page('Founding Members Program', 'founding-members', body)
