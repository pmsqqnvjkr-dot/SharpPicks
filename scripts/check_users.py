#!/usr/bin/env python3
"""
Check user count in production database.
Run with: railway run python scripts/check_users.py
Or locally: DATABASE_URL=postgresql://... python scripts/check_users.py
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    raw = os.environ.get("SQLALCHEMY_DATABASE_URI") or os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_PRIVATE_URL") or ""
    if not raw:
        print("ERROR: No DATABASE_URL found. Set it or run with: railway run python scripts/check_users.py")
        sys.exit(1)

    if raw.startswith("postgres://"):
        raw = "postgresql://" + raw[len("postgres://"):]

    from sqlalchemy import create_engine, text
    engine = create_engine(raw)
    with engine.connect() as conn:
        r = conn.execute(text("SELECT COUNT(*) FROM users"))
        count = r.scalar()
        print(f"Users in database: {count}")
        r = conn.execute(text("SELECT email, created_at FROM users ORDER BY created_at DESC LIMIT 5"))
        rows = r.fetchall()
        print("\nMost recent 5 users:")
        for row in rows:
            print(f"  {row[0]} — {row[1]}")

if __name__ == "__main__":
    main()
