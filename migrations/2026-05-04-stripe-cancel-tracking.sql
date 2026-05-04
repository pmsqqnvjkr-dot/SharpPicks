-- Phase 3 follow-up: full cancellation + trial-conversion tracking on User.
--
-- Audit on 2026-05-04 surfaced four gaps:
--   1. customer.subscription.updated webhook ignored cancel_at_period_end
--      from the payload, so cancellations made via the Stripe Customer
--      Portal didn't update our DB.
--   2. /api/subscriptions/cancel filtered Stripe sub list to
--      status='active', missing trialing subs entirely.
--   3. No timestamp for when a cancellation was scheduled (we knew
--      'cancelling' state but not 'cancelled 3 days ago, 11 days
--      remaining').
--   4. No timestamp for when a trial actually converted to paid.
--
-- This migration adds the three missing columns. The companion code
-- changes wire them up in the webhook handler + cancel endpoint +
-- stripe_metrics source. A one-time backfill script
-- (scripts/backfill_stripe_cancel_state.py) walks every user with a
-- stripe_customer_id, queries live Stripe state, and populates the
-- columns from the source-of-truth Stripe data.

BEGIN;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS cancel_scheduled_at TIMESTAMP NULL,
    ADD COLUMN IF NOT EXISTS cancel_effective_at TIMESTAMP NULL,
    ADD COLUMN IF NOT EXISTS trial_converted_at TIMESTAMP NULL;

CREATE INDEX IF NOT EXISTS ix_users_cancel_scheduled_at ON users (cancel_scheduled_at)
    WHERE cancel_scheduled_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_users_trial_converted_at ON users (trial_converted_at)
    WHERE trial_converted_at IS NOT NULL;

COMMIT;
