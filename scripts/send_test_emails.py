#!/usr/bin/env python3
"""
Send one of each SharpPicks email type to evan@sharppicks.ai for testing.
Uses email_renderer + email_service.send_email only (no Flask app or DB required).
Requires: RESEND_API_KEY (and optional .env in project root).
Run from project root: python scripts/send_test_emails.py
Or: railway run python scripts/send_test_emails.py
"""
import os
import sys
from datetime import datetime, timedelta

# Project root
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
os.chdir(_root)

# Load .env if present
_env_path = os.path.join(_root, ".env")
if os.path.exists(_env_path):
    with open(_env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v

TO = "evan@sharppicks.ai"


def main():
    if not os.environ.get("RESEND_API_KEY"):
        print("ERROR: RESEND_API_KEY not set")
        sys.exit(1)

    from email_renderer import render_template
    from email_service import get_base_url, _make_unsub_url, send_email

    base = get_base_url()
    unsub = _make_unsub_url(TO)
    unsub_signals = _make_unsub_url(TO, "email_signals")
    unsub_results = _make_unsub_url(TO, "email_results")
    unsub_weekly = _make_unsub_url(TO, "email_weekly")
    unsub_marketing = _make_unsub_url(TO, "email_marketing")

    sent = []
    failed = []

    def try_send(name, subject, html):
        try:
            ok = send_email(TO, subject, html)
            (sent if ok else failed).append(name)
        except Exception as e:
            failed.append(f"{name}: {e}")

    # 1. Password reset
    try:
        html = render_template("password-reset", {
            "firstName": "Evan", "resetUrl": f"{base}/reset", "expiresIn": "1 hour",
        })
        try_send("password_reset", "SharpPicks — Password reset requested", html)
    except Exception as e:
        failed.append(f"password_reset: {e}")

    # 2. Verification
    try:
        html = render_template("verification", {
            "firstName": "Evan", "verifyUrl": f"{base}/verify",
        })
        try_send("verification", "SharpPicks — Verify your email", html)
    except Exception as e:
        failed.append(f"verification: {e}")

    # 3. Welcome
    try:
        html = render_template("welcome", {
            "firstName": "Evan", "appUrl": base + "/", "unsubscribeUrl": unsub,
        })
        try_send("welcome", "SharpPicks — Account active", html)
    except Exception as e:
        failed.append(f"welcome: {e}")

    # 4. Trial started
    try:
        end = datetime.now() + timedelta(days=14)
        html = render_template("trial-started", {
            "firstName": "Evan",
            "trialEndDate": end.strftime("%b %-d, %Y"),
            "trialDays": 14,
            "appUrl": base + "/",
            "unsubscribeUrl": unsub,
        })
        try_send("trial_started", "SharpPicks — Trial period active", html)
    except Exception as e:
        failed.append(f"trial_started: {e}")

    # 5. Trial expiring
    try:
        end = datetime.now() + timedelta(days=1)
        html = render_template("trial-expiring", {
            "firstName": "Evan",
            "daysLeft": 1,
            "trialEndDate": end.strftime("%b %-d, %Y"),
            "upgradeUrl": f"{base}/subscribe",
            "unsubscribeUrl": unsub,
        })
        try_send("trial_expiring", "SharpPicks — Trial expires tomorrow", html)
    except Exception as e:
        failed.append(f"trial_expiring: {e}")

    # 6. Trial expired
    try:
        html = render_template("trial-expired", {
            "firstName": "Evan",
            "upgradeUrl": f"{base}/subscribe",
            "unsubscribeUrl": unsub,
        })
        try_send("trial_expired", "SharpPicks — Trial period ended", html)
    except Exception as e:
        failed.append(f"trial_expired: {e}")

    # 7. Cancellation
    try:
        end = datetime.now() + timedelta(days=30)
        html = render_template("cancellation", {
            "firstName": "Evan",
            "accessEndsDate": end.strftime("%b %-d, %Y"),
            "reactivateUrl": f"{base}/subscribe",
            "unsubscribeUrl": unsub,
        })
        try_send("cancellation", "SharpPicks — Subscription cancelled", html)
    except Exception as e:
        failed.append(f"cancellation: {e}")

    # 8. Payment failed
    try:
        html = render_template("payment-failed", {
            "firstName": "Evan",
            "updateUrl": base + "/",
            "unsubscribeUrl": unsub,
        })
        try_send("payment_failed", "SharpPicks — Payment issue", html)
    except Exception as e:
        failed.append(f"payment_failed: {e}")

    # 9. Signal
    try:
        html = render_template("signal", {
            "sport": "NBA",
            "matchup": "Heat @ Celtics",
            "market": "Celtics -4.5",
            "edge": "+7.2%",
            "price": "DraftKings",
            "startTime": "7:30 PM ET",
            "analysis": "Model probability: 58.0% vs market: 52.0%. Projected margin: +5.1",
            "appUrl": base + "/",
            "unsubscribeUrl": unsub_signals,
        })
        try_send("signal", "SharpPicks Signal — Celtics -4.5", html)
    except Exception as e:
        failed.append(f"signal: {e}")

    # 10. Result
    try:
        html = render_template("result", {
            "matchup": "Heat @ Celtics",
            "market": "Celtics -4.5",
            "closeLine": "-5.0",
            "clv": "+0.5",
            "result": "WIN",
            "units": "+1.0u",
            "appUrl": base + "/",
            "unsubscribeUrl": unsub_results,
        })
        try_send("result", "SharpPicks Result — Celtics -4.5 ✓ WIN", html)
    except Exception as e:
        failed.append(f"result: {e}")

    # 11. Weekly summary
    try:
        html = render_template("weekly-summary", {
            "firstName": "Evan",
            "record": "3-1",
            "roi": "+18.4%",
            "units": "+2.7u",
            "passes": 2,
            "avgEdge": "+7.1%",
            "totalRecord": "42-31",
            "periodLabel": "This Week",
            "appUrl": base + "/",
            "unsubscribeUrl": unsub_weekly,
        })
        try_send("weekly_summary", "SharpPicks Weekly — 3-1 · +2.7u · +18.4% ROI", html)
    except Exception as e:
        failed.append(f"weekly_summary: {e}")

    # 12. Founding member
    try:
        html = render_template("founding-member", {
            "firstName": "Evan",
            "foundingNumber": 12,
            "appUrl": base + "/",
            "unsubscribeUrl": unsub,
        })
        try_send("founding_member", "SharpPicks — Founding member status confirmed", html)
    except Exception as e:
        failed.append(f"founding_member: {e}")

    # 13. No signal
    try:
        html = render_template("no-signal", {
            "gamesAnalyzed": 9,
            "edgesDetected": 2,
            "qualifiedSignals": 0,
            "efficiency": "22%",
            "appUrl": base + "/",
            "unsubscribeUrl": unsub_marketing,
        })
        try_send("no_signal", "SharpPicks — Market scan complete · No qualifying signal", html)
    except Exception as e:
        failed.append(f"no_signal: {e}")

    print(f"Sent to {TO}: {len(sent)} emails")
    for name in sent:
        print(f"  ✓ {name}")
    if failed:
        print(f"Failed: {len(failed)}")
        for name in failed:
            print(f"  ✗ {name}")
    if not sent and failed:
        sys.exit(1)
    print("Done.")


if __name__ == "__main__":
    main()
