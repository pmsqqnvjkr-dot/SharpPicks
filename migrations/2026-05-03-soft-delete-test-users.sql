-- Phase 2 cleanup, part 2: soft-delete the 22 known test/spam accounts.
--
-- Companion to 2026-05-03-user-is-internal.sql (which marked them as
-- internal so they don't pollute metrics). This migration adds the
-- separate soft-delete layer that ALSO blocks login for those accounts.
--
-- Important distinction:
--   - @sharppicks.ai accounts: is_internal=true, deleted_at=NULL
--     (excluded from metrics, can still log in)
--   - 22 test/spam accounts:    is_internal=true, deleted_at=NOW()
--     (excluded from metrics AND blocked from login)
--
-- Login enforcement:
--   - User.is_active property returns False when deleted_at IS NOT NULL
--   - Flask-Login's user_loader honors this (rejects session resumption)
--   - Explicit checks added at /api/auth/login, OAuth callbacks, and
--     apple-native sign-in
--
-- Recovery:
--   UPDATE users SET deleted_at = NULL WHERE id = '<uuid>';
-- Hard delete is intentionally not done here — preserves referential
-- integrity from user_events / user_bets / referrals and keeps the door
-- open if a flagged account turns out to be real.

BEGIN;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP NULL;

CREATE INDEX IF NOT EXISTS ix_users_deleted_at ON users (deleted_at)
    WHERE deleted_at IS NOT NULL;

UPDATE users
   SET deleted_at = NOW()
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

COMMIT;
