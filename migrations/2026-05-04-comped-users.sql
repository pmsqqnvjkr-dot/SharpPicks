-- Phase 3 follow-up: distinguish complimentary pro accounts from paying
-- customers. Evan gave free pro access to a small set of friends/family
-- via manual is_premium=True flips. They have full pro access but are
-- not paying — they should NOT count toward MRR, paid totals, or
-- "paid_annual / founding" labels in the admin dashboard.
--
-- Adds a User.comped boolean column. The Stripe metrics source and
-- the user-tag computation both honor it.
--
-- Backfill: marks the four known comped accounts (case-insensitive).
-- donnelly3rd@gmail.com was on the original list but does not yet
-- exist in the DB; left out of the backfill until that account is
-- created. (Add a row to this UPDATE later, or set comped=true
-- manually when the user signs up.)

BEGIN;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS comped BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS ix_users_comped ON users (comped)
    WHERE comped = TRUE;

UPDATE users
   SET comped = TRUE
 WHERE LOWER(email) IN (
    'donnelly3rd@gmail.com',
    'jennaalston21@ymail.com',
    'shaneericmason@gmail.com',
    'barry.j.donnelly@outlook.com',
    'erin.m.donnelly@gmail.com'
 );

COMMIT;
