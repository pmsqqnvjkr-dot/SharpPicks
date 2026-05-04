"""One-off DB-vs-Stripe subscription_status reconciler.

Surfaced 2026-05-04: 9 users had subscription_status='active' in the
DB while Stripe still considered them 'trialing'. Likely cause: a
webhook ordering bug where checkout.session.completed flipped status
to 'active' before customer.subscription.created arrived with the
real 'trialing' state, so the trial flag never got back.

This script walks every real user with a stripe_customer_id, queries
live Stripe state, and updates subscription_status / subscription_plan
/ trial_end_date / current_period_end / cancel_scheduled_at /
cancel_effective_at to match Stripe.

Idempotent — re-running on already-correct rows is a no-op (only
writes when at least one field would change).

Run from project root with:
  python3 scripts/resync_subscription_status.py            # commit
  python3 scripts/resync_subscription_status.py --dry-run  # preview
"""
import argparse
import logging
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('resync')


def _sg(o, k, d=None):
    return o.get(k, d) if isinstance(o, dict) else getattr(o, k, d)


# Map Stripe sub.status to our DB subscription_status. cancel_at_period_end
# refines this further (active+cancel_at_period_end -> 'cancelling';
# trialing+cancel_at_period_end stays 'trial' but cancel fields populated).
def _stripe_to_db_status(stripe_status: str, cancel_at_period_end: bool) -> str:
    if stripe_status == 'active':
        return 'cancelling' if cancel_at_period_end else 'active'
    if stripe_status == 'trialing':
        return 'trial'  # cancel_scheduled_at carries the cancel intent separately
    if stripe_status == 'canceled':
        return 'cancelled'
    if stripe_status == 'past_due':
        return 'past_due'
    if stripe_status in ('unpaid', 'incomplete_expired'):
        return 'expired'
    if stripe_status == 'incomplete':
        return 'pending_verification'  # closest existing bucket
    return stripe_status


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='Preview without writing')
    parser.add_argument('--limit', type=int, default=0, help='Cap users (0 = all)')
    args = parser.parse_args()

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
        log.info('Inspecting %d users with stripe_customer_id', len(users))

        updated = 0
        in_sync = 0
        no_sub = 0
        errors = 0

        for u in users:
            try:
                subs = stripe.Subscription.list(customer=u.stripe_customer_id, status='all', limit=10)
                if not subs.data:
                    no_sub += 1
                    continue

                # Pick the most recently relevant sub: prefer active/trialing,
                # then most recently created.
                target = None
                for s in subs.data:
                    if _sg(s, 'status') in ('active', 'trialing'):
                        target = s
                        break
                if target is None:
                    target = sorted(subs.data, key=lambda s: _sg(s, 'created', 0) or 0, reverse=True)[0]

                stripe_status = _sg(target, 'status')
                cancel_at_period_end = bool(_sg(target, 'cancel_at_period_end'))
                cancel_at_ts = _sg(target, 'cancel_at')
                canceled_at_ts = _sg(target, 'canceled_at')
                trial_end_ts = _sg(target, 'trial_end')
                period_end_ts = _sg(target, 'current_period_end')

                # Pull plan from the first item's price (best-effort)
                items_data = _sg(_sg(target, 'items', {}) or {}, 'data', []) or []
                plan_meta = None
                for item in items_data:
                    md = _sg(_sg(item, 'price', {}) or {}, 'metadata', {}) or {}
                    plan_meta = _sg(md, 'plan') or _sg(md, 'plan_name')
                    if plan_meta:
                        break
                # Fallback: derive plan from interval
                if not plan_meta:
                    rec = _sg(_sg(items_data[0] if items_data else {}, 'price', {}) or {}, 'recurring', {}) or {}
                    interval = _sg(rec, 'interval', '')
                    if interval == 'year':
                        plan_meta = 'annual'
                    elif interval == 'month':
                        plan_meta = 'monthly'

                new_status = _stripe_to_db_status(stripe_status, cancel_at_period_end)
                changes = []

                if u.subscription_status != new_status:
                    changes.append(f'status {u.subscription_status} -> {new_status}')
                    if not args.dry_run:
                        u.subscription_status = new_status

                if plan_meta and (u.subscription_plan or '').lower() != plan_meta.lower():
                    changes.append(f'plan {u.subscription_plan} -> {plan_meta}')
                    if not args.dry_run:
                        u.subscription_plan = plan_meta

                if trial_end_ts:
                    new_trial_end = datetime.utcfromtimestamp(trial_end_ts)
                    if u.trial_end_date != new_trial_end:
                        changes.append(f'trial_end {u.trial_end_date} -> {new_trial_end}')
                        if not args.dry_run:
                            u.trial_end_date = new_trial_end
                            u.trial_ends = new_trial_end

                if period_end_ts:
                    new_period_end = datetime.utcfromtimestamp(period_end_ts)
                    if u.current_period_end != new_period_end:
                        changes.append(f'period_end {u.current_period_end} -> {new_period_end}')
                        if not args.dry_run:
                            u.current_period_end = new_period_end

                # Cancel state
                if cancel_at_period_end:
                    if u.cancel_scheduled_at is None:
                        new_csa = (datetime.utcfromtimestamp(canceled_at_ts) if canceled_at_ts else datetime.utcnow())
                        changes.append(f'cancel_scheduled_at -> {new_csa.isoformat()}')
                        if not args.dry_run:
                            u.cancel_scheduled_at = new_csa
                    if cancel_at_ts:
                        new_cea = datetime.utcfromtimestamp(cancel_at_ts)
                        if u.cancel_effective_at != new_cea:
                            changes.append(f'cancel_effective_at -> {new_cea.isoformat()}')
                            if not args.dry_run:
                                u.cancel_effective_at = new_cea
                else:
                    if u.cancel_scheduled_at is not None or u.cancel_effective_at is not None:
                        changes.append('cleared cancel_scheduled_at + cancel_effective_at')
                        if not args.dry_run:
                            u.cancel_scheduled_at = None
                            u.cancel_effective_at = None

                # is_premium derived from new status
                expected_premium = new_status in ('active', 'trial', 'cancelling')
                if u.is_premium != expected_premium:
                    changes.append(f'is_premium {u.is_premium} -> {expected_premium}')
                    if not args.dry_run:
                        u.is_premium = expected_premium

                if changes:
                    log.info('%s: %s', u.email, '; '.join(changes))
                    updated += 1
                else:
                    in_sync += 1

            except Exception as e:
                errors += 1
                log.error('%s: %s', u.email, e)

        if not args.dry_run:
            db.session.commit()

        log.info('---')
        log.info('Total inspected:   %d', len(users))
        log.info('Updated:           %d', updated)
        log.info('Already in sync:   %d', in_sync)
        log.info('No Stripe sub:     %d', no_sub)
        log.info('Errors:            %d', errors)
        log.info('Dry run' if args.dry_run else 'Committed')


if __name__ == '__main__':
    main()
