#!/usr/bin/env python3
"""
Test Firebase credential loading.
Run from project root. Uses firebase-service-account.json or FIREBASE_* env vars.
  Local:  python scripts/test_firebase_creds.py
  Railway: railway run python scripts/test_firebase_creds.py
"""
import json
import os
import sys

# Minimal credential test without full app deps
def _normalize_pem(s):
    if not s or not isinstance(s, str):
        return s
    s = s.replace("\\n", "\n").replace("\\r", "\r").strip()
    if "-----BEGIN" not in s or "-----END" not in s:
        return s
    import re
    begin, end = "-----BEGIN PRIVATE KEY-----", "-----END PRIVATE KEY-----"
    if "RSA" in s:
        begin, end = "-----BEGIN RSA PRIVATE KEY-----", "-----END RSA PRIVATE KEY-----"
    start = s.find(begin) + len(begin)
    stop = s.find(end)
    if start <= 0 or stop <= start:
        return s
    b64 = re.sub(r"[^A-Za-z0-9+/=]", "", s[start:stop])
    if len(b64) < 100:
        return s
    wrapped = "\n".join(b64[i:i+64] for i in range(0, len(b64), 64))
    return f"{begin}\n{wrapped}\n{end}\n"

def get_info():
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "firebase-service-account.json")
    if os.path.exists(p):
        with open(p) as f:
            info = json.load(f)
        pk = info.get("private_key", "")
        if pk:
            info = dict(info)
            info["private_key"] = _normalize_pem(pk)
        return info
    raw = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON") or ""
    pk = os.environ.get("FIREBASE_PRIVATE_KEY", "").strip()
    email = os.environ.get("FIREBASE_CLIENT_EMAIL", "").strip()
    if pk and email:
        return {
            "type": "service_account",
            "project_id": os.environ.get("FIREBASE_PROJECT_ID", "sharp-picks"),
            "private_key_id": os.environ.get("FIREBASE_PRIVATE_KEY_ID", ""),
            "private_key": _normalize_pem(pk.replace("\\n", "\n")),
            "client_email": email,
            "client_id": "",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "",
            "universe_domain": "googleapis.com",
        }
    if raw:
        raw = raw.strip().strip("'\"")
        try:
            info = json.loads(raw)
            if isinstance(info, dict) and info.get("type") == "service_account":
                pk = info.get("private_key", "")
                if pk:
                    info = dict(info)
                    info["private_key"] = _normalize_pem(pk)
                return info
        except json.JSONDecodeError:
            pass
    return None

def main():
    info = get_info()
    if not info:
        print("ERROR: No credentials. Add firebase-service-account.json or FIREBASE_PRIVATE_KEY + FIREBASE_CLIENT_EMAIL")
        sys.exit(1)
    print("Loaded: project_id=", info.get("project_id"), "client_email=", (info.get("client_email") or "")[:50])
    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request
        creds = service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/firebase.messaging"]
        )
        creds.refresh(Request())
        print("SUCCESS: Credentials validated")
    except Exception as e:
        print("FAILED:", e)
        sys.exit(1)

if __name__ == "__main__":
    main()
