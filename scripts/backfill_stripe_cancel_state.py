"""One-time backfill for the 2026-05-04 cancel-tracking columns.

Walks every User with a stripe_customer_id, queries live Stripe state,
and populates:
  - cancel_scheduled_at  (set when sub.cancel_at_period_end is true)
  - cancel_effective_at  (= sub.cancel_at)
  - trial_converted_at   (best-effort: trial_end_date for users now active
                          who used a trial — this is approximate, not
                          exact, since we can't know the actual conversion
                          moment from historical data)

Idempotent: re-running won't rewrite values that are already non-null.

Run from the project root with:
  python3 scripts/backfill_stripe_cancel_state.py
or with a dry-run preview:
  python3 scripts/backfill_stripe_cancel_state.py --dry-run
"""
import argparse
import logging
import os
import sys
from datetime import datetime

# Allow running from project root: ensure we can import the Flask app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('backfill')


def _get(o, k, d=None):
    return o.get(k, d) if isinstance(o, dict) else getattr(o, k, d)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='Print what would change without writing')
    parser.add_argument('--limit', type=int, default=0, help='Cap users processed (0 = all)')
    args = parser.parse_args()

    # Late imports so the Flask app context is available
    from app import app
    from models import db, User
    from stripe_client import get_stripe_client

    stripe = get_stripe_client()

    with app.app_context():
        users = User.query.filter(
            User.stripe_customer_id.isnot(None),
            User.deleted_at.is_(None),
        ).all()
        if args.limit:
            users = users[:args.limit]
        log.info('Found %d users with stripe_customer_id to inspect', len(users))

        updated = 0
        cancel_set = 0
        trial_converted_set = 0
        skipped_already = 0
        errors = 0

        for u in users:
            try:
                subs = stripe.Subscription.list(customer=u.stripe_customer_id, status='all', limit=10)
                if not subs.data:
                    continue
                # Pick the most recently active/trialing sub; fall back to most recent overall
                target = None
                for s in subs.data:
                    if _get(s, 'status') in ('active', 'trialing'):
                        target = s
                        break
                if target is None:
                    target = subs.data[0]

                status = _get(target, 'status')
                cancel_at_pe = bool(_get(target, 'cancel_at_period_end'))
                cancel_at = _get(target, 'cancel_at')
                canceled_at = _get(target, 'canceled_at')

                changes = []

                # cancel_scheduled_at
                if cancel_at_pe and u.cancel_scheduled_at is None:
                    new_val = (
                        datetime.fromtimestamp(canceled_at) if canceled_at else datetime.utcnow()
                    )
                    if not args.dry_run:
                        u.cancel_scheduled_at = new_val
                    changes.append(f'cancel_scheduled_at={new_val.isoformat()}')
                    cancel_set += 1

                # cancel_effective_at
                if cancel_at and u.cancel_effective_at is None:
                    new_val = datetime.fromtimestamp(cancel_at)
                    if not args.dry_run:
                        u.cancel_effective_at = new_val
                    changes.append(f'cancel_effective_at={new_val.isoformat()}')

                # subscription_status alignment: if Stripe says cancel scheduled
                # and we still have them as 'active' or 'trial', flip to 'cancelling'
                if cancel_at_pe and u.subscription_status in ('active', 'trial'):
                    if not args.dry_run:
                        u.subscription_status = 'cancelling'
                    changes.append('subscription_status=cancelling')

                # trial_converted_at — best-effort backfill: if user is currently
                # active, has trial_used=True, and trial_end_date is in the past,
                # use trial_end_date as the conversion proxy. This is approximate
                # but the only data we have from history.
                if (status == 'active'
                        and u.trial_used
                        and u.trial_end_date
                        and u.trial_end_date < datetime.utcnow()
                        and u.trial_converted_at is None):
                    if not args.dry_run:
                        u.trial_converted_at = u.trial_end_date
                    changes.append(f'trial_converted_at={u.trial_end_date.isoformat()} (approx from trial_end_date)')
                    trial_converted_set += 1

                if changes:
                    log.info('%s: %s', u.email, '; '.join(changes))
                    updated += 1
                else:
                    skipped_already += 1

            except Exception as e:
                errors += 1
                log.error('%s: %s', u.email, e)

        if not args.dry_run:
            db.session.commit()

        log.info('---')
        log.info('Users inspected:           %d', len(users))
        log.info('Users updated:             %d', updated)
        log.info('Cancel-scheduled set:      %d', cancel_set)
        log.info('Trial-converted set:       %d (approx from trial_end_date)', trial_converted_set)
        log.info('Skipped (already populated or no change): %d', skipped_already)
        log.info('Errors:                    %d', errors)
        log.info('Dry run' if args.dry_run else 'Committed')


if __name__ == '__main__':
    main()
