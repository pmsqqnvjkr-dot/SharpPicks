#!/usr/bin/env bash
# Clone the SharpPicks production database into the QA database.
#
# Run this from your local machine (not Railway). Requires `pg_dump` and
# `psql` installed locally (Postgres client tools).
#
# Required env vars:
#   PROD_DATABASE_URL  — source database (read access is sufficient)
#   QA_DATABASE_URL    — destination database (will be wiped + restored)
#
# Optional flag:
#   --sanitize-emails  — replace every user.email with qa+<id>@sharppicks.ai
#                        (belt-and-suspenders alongside EMAIL_OVERRIDE_TO)
#
# How to grab the URLs:
#   PROD: Railway → SharpPicks project → production env → Postgres service
#         → Variables → DATABASE_URL (or DATABASE_PUBLIC_URL for the
#         externally-reachable one)
#   QA:   Same path, but pick the staging environment first.
#
# Usage:
#   export PROD_DATABASE_URL="postgresql://..."
#   export QA_DATABASE_URL="postgresql://..."
#   ./scripts/clone_prod_to_qa.sh
#
# Or one-shot:
#   PROD_DATABASE_URL="..." QA_DATABASE_URL="..." ./scripts/clone_prod_to_qa.sh
#
# Safe to run repeatedly. Existing QA data is dropped via --clean.

set -euo pipefail

PROD="${PROD_DATABASE_URL:-}"
QA="${QA_DATABASE_URL:-}"

if [ -z "$PROD" ] || [ -z "$QA" ]; then
  echo "ERROR: Both PROD_DATABASE_URL and QA_DATABASE_URL must be set."
  echo "       Grab them from Railway → Postgres service → Variables."
  exit 1
fi

if [ "$PROD" = "$QA" ]; then
  echo "ERROR: PROD_DATABASE_URL and QA_DATABASE_URL are identical."
  echo "       Refusing to clone the prod database over itself."
  exit 1
fi

# Show a redacted summary, then ask for explicit confirmation.
prod_host=$(echo "$PROD" | sed -E 's#.*@([^:/]+).*#\1#')
qa_host=$(echo "$QA" | sed -E 's#.*@([^:/]+).*#\1#')

echo "About to:"
echo "  WIPE the database at: $qa_host"
echo "  REPLACE with a dump from: $prod_host"
echo ""
read -p "Type 'CLONE' to proceed (anything else aborts): " conf
if [ "$conf" != "CLONE" ]; then
  echo "Aborted."
  exit 1
fi

echo ""
echo "[1/3] Streaming pg_dump from prod into psql against QA..."
pg_dump "$PROD" \
  --no-owner --no-acl \
  --clean --if-exists \
  | psql "$QA" -v ON_ERROR_STOP=1 -q

echo ""
echo "[2/3] Disabling FCM tokens and clearing session tokens in QA..."
# This prevents two specific accidents:
#  - a QA push attempt firing on a real device that's still in the table
#  - a stale prod session cookie being reused to log into QA
psql "$QA" -v ON_ERROR_STOP=1 <<'SQL'
UPDATE fcm_tokens SET enabled = FALSE;
UPDATE users SET session_token = NULL;
SQL

if [ "${1:-}" = "--sanitize-emails" ]; then
  echo ""
  echo "[3/3] Sanitizing user emails to qa+<id>@sharppicks.ai..."
  psql "$QA" -v ON_ERROR_STOP=1 <<'SQL'
UPDATE users
   SET email = 'qa+' || id || '@sharppicks.ai',
       email_normalized = 'qa+' || id || '@sharppicks.ai';
SQL
else
  echo ""
  echo "[3/3] Skipping email sanitization (pass --sanitize-emails to enable)."
  echo "      Rely on EMAIL_OVERRIDE_TO env var in the staging environment"
  echo "      to keep outbound mail off real users."
fi

echo ""
echo "Done. QA database now matches prod as of $(date)."
