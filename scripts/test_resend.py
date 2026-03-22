#!/usr/bin/env python3
"""
Test Resend API key for sending email.
Run: python scripts/test_resend.py  (loads .env if present)
Or:  railway run python scripts/test_resend.py
"""
import os
import sys

# Load .env if present
_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(_env_path):
    with open(_env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v

def main():
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        print("ERROR: RESEND_API_KEY not set")
        sys.exit(1)

    # Test 1: API key validity (domains endpoint)
    try:
        import requests
        resp = requests.get(
            "https://api.resend.com/domains",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=8,
        )
        if resp.status_code in (401, 403):
            print("FAILED: Invalid API key (401/403)")
            sys.exit(1)
        if resp.status_code != 200:
            print(f"WARN: Domains API returned {resp.status_code}")
    except Exception as e:
        print(f"FAILED (connect): {e}")
        sys.exit(1)

    # Test 2: Send a test email (to ourselves)
    to_email = os.environ.get("TEST_EMAIL", "evan@sharppicks.ai")
    try:
        import resend
        resend.api_key = api_key
        r = resend.Emails.send({
            "from": "SharpPicks <info@sharppicks.ai>",
            "to": [to_email],
            "subject": "Resend test — SharpPicks",
            "html": "<p>This is a test. Your Resend key works.</p>",
        })
        print(f"SUCCESS: Test email sent to {to_email} (id={r.get('id', 'N/A')})")
    except Exception as e:
        print(f"FAILED (send): {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
