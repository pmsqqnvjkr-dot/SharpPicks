-- Backfill for the invoice.paid bug fixed in app.py:7117 today.
-- The webhook used to flip subscription_status='active' for the $0
-- trial-start invoice that Stripe fires when a sub is created with a
-- trial. Result: users who are still in their Stripe trial were
-- showing 'paid' pills in the admin Users tab.
--
-- Reset any user whose Stripe trial is still in flight back to 'trial'.
-- Heuristic: status='active' but trial_end_date is in the future and
-- trial_converted_at is NULL (never paid a real invoice).

BEGIN;

UPDATE users
   SET subscription_status = 'trial'
 WHERE subscription_status = 'active'
   AND trial_end_date IS NOT NULL
   AND trial_end_date > NOW()
   AND trial_converted_at IS NULL;

COMMIT;
