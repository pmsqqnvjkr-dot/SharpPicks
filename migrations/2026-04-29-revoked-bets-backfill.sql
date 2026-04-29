-- One-time backfill for tracked bets orphaned by past revoke events.
-- Run against production AFTER commit 1+2 ship and stay green for 24 hours.
-- Acceptance check: SELECT COUNT(*) FROM tracked_bets WHERE result IS NULL
--   AND pick_id IN (SELECT id FROM picks WHERE result = 'revoked');
-- Should return 0 after this runs.

UPDATE tracked_bets tb
SET result = 'revoked'
FROM picks p
WHERE tb.pick_id = p.id
  AND tb.result IS NULL
  AND p.result = 'revoked';
