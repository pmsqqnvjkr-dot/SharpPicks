-- Soft-delete sandbox@test.com test account.
--
-- Same pattern as 2026-05-03-soft-delete-test-users.sql:
--   - is_internal=true     -> excluded from admin/customer metrics
--   - deleted_at=NOW()     -> User.is_active returns False, login blocked
--
-- Hard delete is intentionally not used. Referential integrity from
-- user_events / user_bets / tracked_bets / referrals is preserved, and
-- recovery is a single UPDATE if the account turns out to be needed.
--
-- Recovery:
--   UPDATE users SET is_internal = false, deleted_at = NULL
--    WHERE LOWER(email) = 'sandbox@test.com';
--
-- Verify after running:
--   SELECT id, email, is_internal, deleted_at FROM users
--    WHERE LOWER(email) = 'sandbox@test.com';
--   -- expect is_internal=true, deleted_at IS NOT NULL

BEGIN;

UPDATE users
   SET is_internal = true,
       deleted_at = NOW()
 WHERE LOWER(email) = 'sandbox@test.com';

-- Backfill is_internal=true onto this user's user_events so the
-- event-level metrics filter catches them without needing a join.
UPDATE user_events ue
   SET is_internal = true
  FROM users u
 WHERE ue.user_id = u.id
   AND LOWER(u.email) = 'sandbox@test.com'
   AND ue.is_internal = false;

COMMIT;
