-- Phase 2 cleanup: mark internal/test users so they don't pollute admin metrics.
--
-- "Internal" here means: any user whose data should not count toward growth,
-- conversion, or activity metrics on the Command Center dashboard. Two
-- categories qualify:
--   1. Anyone with an @sharppicks.ai email (employees / Evan / shared accounts)
--   2. The known list of test/spam signups identified during cleanup on
--      2026-05-03
--
-- This is a soft-exclude (Option A from the discussion): the users still
-- exist, can still log in, are still tracked in user_events. The admin
-- metrics endpoints filter them out by default and respect the existing
-- ?include_internal=true query param to opt them back in.
--
-- After running, verify:
--   - new column users.is_internal exists, NOT NULL DEFAULT false
--   - row count where is_internal=true ~= count(emails LIKE '%@sharppicks.ai')
--     plus the 21 test emails that exist in the table
--   - all 5588 evan@sharppicks.ai user_events rows still have is_internal=true
--     (this was set in the 2026-05-01 migration; nothing here touches those)
--   - new index ix_users_is_internal exists for fast filter

BEGIN;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS is_internal BOOLEAN NOT NULL DEFAULT false;

CREATE INDEX IF NOT EXISTS ix_users_is_internal ON users (is_internal)
    WHERE is_internal = true;

-- Auto-flag every @sharppicks.ai address (case-insensitive)
UPDATE users
   SET is_internal = true
 WHERE LOWER(email) LIKE '%@sharppicks.ai';

-- Manually flag the known test/spam signups identified on 2026-05-03.
-- These were tester accounts and a wave of likely-spam signups (geo cluster
-- from a referral attribution scam). Confirmed with Evan as not real users.
UPDATE users
   SET is_internal = true
 WHERE LOWER(email) IN (
    'test@gmail.com',
    'john.doe@example.com',
    'c.kirsipuu@gmail.com',
    'jfuqua414@gmail.com',
    'rashindkhan33@gmail.com',
    'asma.asma.asma.2026@gmail.com',
    'belalahmady140@gmail.com',
    'barakatullah1provider@gmail.com',
    'ali133afghan@gmail.com',
    'shahidonkhadim@gmail.com',
    'baraktullahkhan12@gmail.com',
    'shamskhan123408@gmail.com',
    'khalidkhadem2024@gmail.com',
    'abdullahkhankhan2026@gmail.com',
    'afg.arian123@gmail.com',
    'afqaseem866@gmail.com',
    'abasskhan9995@gmail.com',
    'abobakerkhan95@gmail.com',
    'khadimtester@gmail.com',
    'ksofian023@gmail.com',
    'shahidkhadem062@gmail.com',
    'hakeemkhan0003@gmail.com'
 );

-- Propagate is_internal=true onto existing user_events rows for newly-flagged
-- users so the events-source filter (which filters at the event level for
-- query speed) catches them without a join. Any rows already flagged stay
-- flagged. Anonymous events (user_id IS NULL) are untouched.
UPDATE user_events ue
   SET is_internal = true
  FROM users u
 WHERE ue.user_id = u.id
   AND u.is_internal = true
   AND ue.is_internal = false;

COMMIT;
