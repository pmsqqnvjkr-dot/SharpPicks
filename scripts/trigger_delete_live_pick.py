#!/usr/bin/env python3
"""Call clear-today on production to remove the live pick. Needs CRON_SECRET in .env."""
import os
import sys
_env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(_env):
    with open(_env) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v

def main():
    secret = os.environ.get("CRON_SECRET")
    base = os.environ.get("APP_BASE_URL", "https://app.sharppicks.ai").rstrip("/")
    url = f"{base}/api/admin/clear-today"
    if not secret:
        print("ERROR: CRON_SECRET not set in .env")
        sys.exit(1)
    import requests
    r = requests.post(url, headers={"X-Cron-Secret": secret}, json={"sport": "nba"}, timeout=15)
    print(r.status_code, r.text[:500] if len(r.text) > 500 else r.text)
    if r.status_code not in (200, 201):
        sys.exit(1)

if __name__ == "__main__":
    main()
