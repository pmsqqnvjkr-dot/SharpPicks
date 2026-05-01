#!/usr/bin/env python3
"""
PRE-MIGRATION CHECK — read-only.

Two safety checks before applying migrations/2026-05-01-extend-user-events.sql:

1. Confirm the users table is named 'users' (plural). The FK in models.py
   references 'users.id'; verifying the live schema matches.
2. Backfill dry-run: count rows in user_events that the migration's
   UPDATE would flip to is_internal = true. Expected ~5588 (matches the
   audit count for evan@sharppicks.ai).

If check 1 returns no row for 'users', or check 2 returns 0 / wildly
different from 5588, STOP and surface — the migration would silently no-op
or target the wrong table.

Run with DATABASE_URL sourced from environment, never inlined:
    set -a && source .env && set +a
    python3 scripts/precheck_user_events_backfill.py
"""
import os
import sys

from sqlalchemy import create_engine, text


def main():
    raw = (
        os.environ.get("SQLALCHEMY_DATABASE_URI")
        or os.environ.get("DATABASE_URL")
        or os.environ.get("DATABASE_PRIVATE_URL")
        or ""
    )
    if not raw:
        print("ERROR: No DATABASE_URL in environment.", file=sys.stderr)
        sys.exit(1)
    if raw.startswith("postgres://"):
        raw = "postgresql://" + raw[len("postgres://"):]

    engine = create_engine(raw)
    with engine.connect() as conn:
        print("=== Check 2: tables matching user* ===")
        rows = conn.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name LIKE 'user%' "
            "ORDER BY table_name"
        )).fetchall()
        for r in rows:
            print(f"  {r._mapping['table_name']}")
        names = {r._mapping['table_name'] for r in rows}
        if 'users' not in names:
            print("  WARNING: 'users' (plural) not found in user* tables.")

        print()
        print("=== Check 1: backfill dry-run count ===")
        n = conn.execute(text(
            "SELECT COUNT(*) FROM user_events ue "
            "JOIN users u ON ue.user_id = u.id "
            "WHERE lower(u.email) = 'evan@sharppicks.ai'"
        )).scalar()
        print(f"  rows that WOULD be flipped to is_internal=true: {n}")

        print()
        print("=== Sanity: how many users with that email? ===")
        nu = conn.execute(text(
            "SELECT COUNT(*) FROM users WHERE lower(email) = 'evan@sharppicks.ai'"
        )).scalar()
        print(f"  users matching evan@sharppicks.ai: {nu}")

        print()
        print("=== Sanity: distinct user_ids tied to those events ===")
        for r in conn.execute(text(
            "SELECT u.id, u.email, COUNT(ue.id) AS event_count "
            "FROM users u "
            "JOIN user_events ue ON ue.user_id = u.id "
            "WHERE lower(u.email) = 'evan@sharppicks.ai' "
            "GROUP BY u.id, u.email"
        )).fetchall():
            m = r._mapping
            print(f"  user_id={m['id']} email={m['email']} events={m['event_count']}")


if __name__ == "__main__":
    main()
