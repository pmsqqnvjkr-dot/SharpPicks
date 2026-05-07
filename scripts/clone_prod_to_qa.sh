#!/usr/bin/env bash
# Clone the SharpPicks production data into the QA environment.
#
# SharpPicks runs a two-database split:
#   1. Postgres holds users, picks, tracked_bets, edge_snapshots, etc.
#      Cloned via pg_dump | psql.
#   2. SQLite at $RAILWAY_VOLUME_MOUNT_PATH/sharp_picks.db holds the games
#      tables (NBA / MLB / WNBA), line_snapshots, daily_market_reports
#      (the MEI history table that drives the sparkline), nba_player_props,
#      and wnba_rolling_ratings. Cloned via railway ssh + base64 pipe.
#
# Run this from your local machine. Requires:
#   - pg_dump + psql (Postgres client tools)
#   - railway CLI logged in to the SharpPicks workspace, with access to
#     both the prod and QA services
#
# Required env vars:
#   PROD_DATABASE_URL     — source Postgres
#   QA_DATABASE_URL       — destination Postgres (will be wiped + restored)
#   PROD_RAILWAY_SERVICE  — service name in prod env (e.g. "sharppicks")
#   QA_RAILWAY_SERVICE    — service name in staging env (e.g. "sharppicks")
#   PROD_RAILWAY_ENV      — env name in prod (default: "production")
#   QA_RAILWAY_ENV        — env name in staging (default: "staging")
#
# Optional flags:
#   --sanitize-emails  — replace every user.email with qa+<id>@sharppicks.ai
#   --skip-postgres    — skip the pg_dump | psql step
#   --skip-sqlite      — skip the SQLite volume clone step
#
# Usage:
#   export PROD_DATABASE_URL="postgresql://..."
#   export QA_DATABASE_URL="postgresql://..."
#   export PROD_RAILWAY_SERVICE="sharppicks"
#   export QA_RAILWAY_SERVICE="sharppicks"
#   ./scripts/clone_prod_to_qa.sh
#
# Safe to run repeatedly. Existing QA data is dropped and replaced.

set -euo pipefail

PROD="${PROD_DATABASE_URL:-}"
QA="${QA_DATABASE_URL:-}"
PROD_SVC="${PROD_RAILWAY_SERVICE:-}"
QA_SVC="${QA_RAILWAY_SERVICE:-}"
PROD_ENV="${PROD_RAILWAY_ENV:-production}"
QA_ENV="${QA_RAILWAY_ENV:-staging}"

SANITIZE_EMAILS=false
SKIP_PG=false
SKIP_SQLITE=false
for arg in "$@"; do
  case "$arg" in
    --sanitize-emails) SANITIZE_EMAILS=true ;;
    --skip-postgres)   SKIP_PG=true ;;
    --skip-sqlite)     SKIP_SQLITE=true ;;
    *) echo "Unknown flag: $arg" >&2; exit 1 ;;
  esac
done

if [ "$SKIP_PG" = false ]; then
  if [ -z "$PROD" ] || [ -z "$QA" ]; then
    echo "ERROR: PROD_DATABASE_URL and QA_DATABASE_URL must be set"
    echo "       (or pass --skip-postgres if you only want to clone SQLite)."
    exit 1
  fi
  if [ "$PROD" = "$QA" ]; then
    echo "ERROR: PROD_DATABASE_URL and QA_DATABASE_URL are identical."
    exit 1
  fi
fi

if [ "$SKIP_SQLITE" = false ]; then
  if [ -z "$PROD_SVC" ] || [ -z "$QA_SVC" ]; then
    echo "ERROR: PROD_RAILWAY_SERVICE and QA_RAILWAY_SERVICE must be set"
    echo "       (or pass --skip-sqlite if you only want to clone Postgres)."
    exit 1
  fi
  if ! command -v railway >/dev/null 2>&1; then
    echo "ERROR: railway CLI not installed. Install with:"
    echo "         npm install -g @railway/cli && railway login"
    echo "       Or pass --skip-sqlite to skip the SQLite step."
    exit 1
  fi
fi

prod_host="(skipped)"
qa_host="(skipped)"
if [ "$SKIP_PG" = false ]; then
  prod_host=$(echo "$PROD" | sed -E 's#.*@([^:/]+).*#\1#')
  qa_host=$(echo "$QA" | sed -E 's#.*@([^:/]+).*#\1#')
fi

echo "About to:"
[ "$SKIP_PG" = false ] && {
  echo "  WIPE Postgres at: $qa_host"
  echo "  REPLACE with dump from: $prod_host"
}
[ "$SKIP_SQLITE" = false ] && {
  echo "  WIPE SQLite volume on Railway service: $QA_SVC ($QA_ENV)"
  echo "  REPLACE with snapshot from service: $PROD_SVC ($PROD_ENV)"
}
echo ""
read -p "Type 'CLONE' to proceed (anything else aborts): " conf
if [ "$conf" != "CLONE" ]; then
  echo "Aborted."
  exit 1
fi

# ─── Postgres ──────────────────────────────────────────────────────────────
if [ "$SKIP_PG" = false ]; then
  echo ""
  echo "[postgres 1/2] Streaming pg_dump from prod into psql against QA..."
  pg_dump "$PROD" \
    --no-owner --no-acl \
    --clean --if-exists \
    | psql "$QA" -v ON_ERROR_STOP=1 -q

  echo ""
  echo "[postgres 2/2] Disabling FCM tokens and clearing session tokens in QA..."
  psql "$QA" -v ON_ERROR_STOP=1 <<'SQL'
UPDATE fcm_tokens SET enabled = FALSE;
UPDATE users SET session_token = NULL;
SQL

  if [ "$SANITIZE_EMAILS" = true ]; then
    echo ""
    echo "[postgres extra] Sanitizing user emails to qa+<id>@sharppicks.ai..."
    psql "$QA" -v ON_ERROR_STOP=1 <<'SQL'
UPDATE users
   SET email = 'qa+' || id || '@sharppicks.ai',
       email_normalized = 'qa+' || id || '@sharppicks.ai';
SQL
  fi
else
  echo ""
  echo "[postgres] Skipped (--skip-postgres)."
fi

# ─── SQLite (Railway volume) ───────────────────────────────────────────────
if [ "$SKIP_SQLITE" = false ]; then
  TEMP=$(mktemp -d)
  trap 'rm -rf "$TEMP"' EXIT

  echo ""
  echo "[sqlite 1/3] Snapshotting prod SQLite via railway ssh..."
  # Use VACUUM INTO to get a consistent snapshot even if the prod app is
  # actively writing. Then base64-stream it back to local. The DB lives at
  # $RAILWAY_VOLUME_MOUNT_PATH/sharp_picks.db on the volume.
  railway ssh --service "$PROD_SVC" --environment "$PROD_ENV" -- \
    bash -lc '
      set -euo pipefail
      DB="${RAILWAY_VOLUME_MOUNT_PATH:-/data}/sharp_picks.db"
      SNAP="/tmp/sharp_picks.snap.$$.db"
      sqlite3 "$DB" "VACUUM INTO '"'"'$SNAP'"'"'"
      base64 < "$SNAP"
      rm -f "$SNAP"
    ' > "$TEMP/prod.b64"

  echo "[sqlite 2/3] Decoding snapshot locally..."
  base64 -d < "$TEMP/prod.b64" > "$TEMP/sharp_picks.db"
  bytes=$(stat -f%z "$TEMP/sharp_picks.db" 2>/dev/null || stat -c%s "$TEMP/sharp_picks.db")
  echo "             Snapshot size: ${bytes} bytes"

  # Sanity check: file is a valid SQLite database
  if ! sqlite3 "$TEMP/sharp_picks.db" "SELECT count(*) FROM sqlite_master" >/dev/null 2>&1; then
    echo "ERROR: snapshot is not a valid SQLite file. Aborting before QA write."
    exit 1
  fi
  tables=$(sqlite3 "$TEMP/sharp_picks.db" "SELECT count(*) FROM sqlite_master WHERE type='table'")
  mei_rows=$(sqlite3 "$TEMP/sharp_picks.db" "SELECT count(*) FROM daily_market_reports" 2>/dev/null || echo "?")
  echo "             Tables: ${tables}, daily_market_reports rows: ${mei_rows}"

  echo "[sqlite 3/3] Restoring snapshot into QA volume via railway ssh..."
  # Atomic-rename so QA app readers don't see a partial file. WAL/SHM
  # sidecar files from the previous DB are stale and removed.
  base64 < "$TEMP/sharp_picks.db" | \
    railway ssh --service "$QA_SVC" --environment "$QA_ENV" -- \
    bash -lc '
      set -euo pipefail
      DB="${RAILWAY_VOLUME_MOUNT_PATH:-/data}/sharp_picks.db"
      TMP="${DB}.restore.$$"
      base64 -d > "$TMP"
      mv "$TMP" "$DB"
      rm -f "${DB}-wal" "${DB}-shm"
      echo "Restored $(stat -c%s "$DB") bytes to $DB"
    '
else
  echo ""
  echo "[sqlite] Skipped (--skip-sqlite)."
fi

echo ""
echo "Done. QA now matches prod as of $(date)."
echo "Verify in QA UI: MEI sparkline, today's slate, market reports."
