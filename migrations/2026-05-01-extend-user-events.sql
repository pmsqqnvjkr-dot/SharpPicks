-- Phase 1 Step 1.1: extend user_events with surface, is_internal, signal_id,
-- sport, client_ts, ip, user_agent, and matching indexes. Backfill is_internal
-- for rows whose user.email matches the internal allowlist
-- (evan@sharppicks.ai).
--
-- Column-name mapping notes (Phase 1 spec -> existing schema):
--   event       -> event_type   (existing column kept; server maps on write)
--   server_ts   -> created_at   (existing column kept)
-- The composite index therefore lives on (event_type, created_at DESC).
--
-- Pre-checks expected before running (see scripts/precheck_user_events_backfill.py):
--   - public.users (plural) exists; FK ue.user_id -> users.id resolves
--   - backfill dry-run row count = 5588 for evan@sharppicks.ai
--
-- After running, verify:
--   - 7 new columns visible in information_schema.columns for user_events
--   - 2 new indexes: ix_user_events_event_type_created_at, ix_user_events_surface
--   - total user_events row count unchanged
--   - is_internal=true row count = pre-migration evan event count (~5588)

BEGIN;

ALTER TABLE user_events
  ADD COLUMN IF NOT EXISTS surface     TEXT,
  ADD COLUMN IF NOT EXISTS is_internal BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS signal_id   TEXT,
  ADD COLUMN IF NOT EXISTS sport       TEXT,
  ADD COLUMN IF NOT EXISTS client_ts   TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS ip          INET,
  ADD COLUMN IF NOT EXISTS user_agent  TEXT;

CREATE INDEX IF NOT EXISTS ix_user_events_event_type_created_at
  ON user_events (event_type, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_user_events_surface
  ON user_events (surface);

-- (user_id index already exists as ix_user_events_user_id)

UPDATE user_events ue
   SET is_internal = true
  FROM users u
 WHERE ue.user_id = u.id
   AND lower(u.email) = 'evan@sharppicks.ai';

COMMIT;
