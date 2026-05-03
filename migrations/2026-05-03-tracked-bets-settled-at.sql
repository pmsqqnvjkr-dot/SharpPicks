-- Add settled_at to tracked_bets for audit + stale-pending nudges later.
-- The app boot path also runs ALTER + backfill, but ship this for ops parity.
-- Acceptance check: SELECT COUNT(*) FROM tracked_bets
--   WHERE result IS NOT NULL AND settled_at IS NULL;
-- Should return 0 after this runs.

ALTER TABLE tracked_bets ADD COLUMN IF NOT EXISTS settled_at TIMESTAMP;

UPDATE tracked_bets
SET settled_at = created_at
WHERE settled_at IS NULL
  AND result IS NOT NULL;
