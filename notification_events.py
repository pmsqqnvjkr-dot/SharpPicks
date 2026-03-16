"""
Canonical notification event dispatcher.

Coordinates push notifications (via notification_service) and emails
(via email_service) for all product events. Each event is configured
with preference keys and whether it targets premium users only.
"""

import logging


NOTIFICATION_EVENTS = {
    'pick_published': {
        'push_fn': 'send_pick_notification',
        'email_fn': 'send_signal_email',
        'email_pref': 'email_signals',
        'premium_only': True,
        'description': 'New model signal published',
    },
    'pick_graded': {
        'push_fn': 'send_result_notification',
        'email_fn': 'send_result_email',
        'email_pref': 'email_results',
        'premium_only': True,
        'description': 'Signal graded (win/loss/push)',
    },
    'pass_generated': {
        'push_fn': 'send_pass_notification',
        'email_fn': 'send_no_signal_email',
        'email_pref': 'email_marketing',
        'premium_only': True,
        'description': 'No qualifying signal today',
    },
    'trial_started': {
        'push_fn': None,
        'email_fn': 'send_trial_started_email',
        'email_pref': None,
        'premium_only': False,
        'description': 'Trial activated for new user',
    },
    'founding_member': {
        'push_fn': None,
        'email_fn': 'send_founding_member_email',
        'email_pref': None,
        'premium_only': False,
        'description': 'Founding member status confirmed',
    },
    'journal_published': {
        'push_fn': 'send_journal_notification',
        'email_fn': None,
        'email_pref': None,
        'premium_only': True,
        'description': 'New journal article published',
    },
    'weekly_summary': {
        'push_fn': 'send_weekly_summary_notification',
        'email_fn': 'send_weekly_summary',
        'email_pref': 'email_weekly',
        'premium_only': True,
        'description': 'Weekly performance recap',
    },
}


def get_email_recipients(event_name):
    """Return list of (user_id, email, first_name) for users eligible for this event.

    Respects premium_only flag and per-user email preferences.
    """
    config = NOTIFICATION_EVENTS.get(event_name)
    if not config:
        logging.warning(f"Unknown notification event: {event_name}")
        return []

    try:
        from models import User
        query = User.query.filter(User.email.isnot(None))

        if config['premium_only']:
            query = query.filter(
                (User.is_premium == True) |
                (User.subscription_status.in_(['active', 'trial']))
            )

        users = query.all()
        recipients = []
        pref_key = config.get('email_pref')

        for user in users:
            if not user.email:
                continue
            if pref_key:
                prefs = user.notification_prefs or {}
                if not prefs.get(pref_key, True):
                    continue
            recipients.append((user.id, user.email, user.first_name))

        return recipients
    except Exception as e:
        logging.error(f"get_email_recipients({event_name}) failed: {e}")
        return []


def dispatch_signal_emails(pick):
    """Send signal email to all eligible premium users."""
    try:
        from email_service import send_signal_email
        recipients = get_email_recipients('pick_published')
        sent = 0
        for user_id, email, first_name in recipients:
            try:
                if send_signal_email(email, pick):
                    sent += 1
            except Exception as e:
                logging.error(f"Signal email to {email} failed: {e}")
        logging.info(f"Signal emails dispatched: {sent}/{len(recipients)}")
        return sent
    except Exception as e:
        logging.error(f"dispatch_signal_emails failed: {e}")
        return 0


def dispatch_result_emails(pick):
    """Send result email to all eligible premium users."""
    try:
        from email_service import send_result_email
        recipients = get_email_recipients('pick_graded')
        sent = 0
        for user_id, email, first_name in recipients:
            try:
                if send_result_email(email, pick):
                    sent += 1
            except Exception as e:
                logging.error(f"Result email to {email} failed: {e}")
        logging.info(f"Result emails dispatched: {sent}/{len(recipients)}")
        return sent
    except Exception as e:
        logging.error(f"dispatch_result_emails failed: {e}")
        return 0


def dispatch_no_signal_emails(games_analyzed=0, edges_detected=0, efficiency=0):
    """Send no-signal email to all eligible premium users."""
    try:
        from email_service import send_no_signal_email
        recipients = get_email_recipients('pass_generated')
        sent = 0
        for user_id, email, first_name in recipients:
            try:
                if send_no_signal_email(email, games_analyzed, edges_detected, efficiency):
                    sent += 1
            except Exception as e:
                logging.error(f"No-signal email to {email} failed: {e}")
        logging.info(f"No-signal emails dispatched: {sent}/{len(recipients)}")
        return sent
    except Exception as e:
        logging.error(f"dispatch_no_signal_emails failed: {e}")
        return 0


def dispatch_trial_started_email(user):
    """Send trial started email to a single user."""
    try:
        from email_service import send_trial_started_email
        trial_start = getattr(user, 'trial_start_date', None) or getattr(user, 'created_at', None)
        trial_end = getattr(user, 'trial_ends', None) or getattr(user, 'trial_end_date', None)
        return send_trial_started_email(user.email, trial_start, trial_end)
    except Exception as e:
        logging.error(f"dispatch_trial_started_email failed for {getattr(user, 'email', '?')}: {e}")
        return False


def dispatch_founding_member_email(user):
    """Send founding member confirmation email to a single user."""
    try:
        from email_service import send_founding_member_email
        return send_founding_member_email(
            user.email,
            member_number=user.founding_number,
            total=100,
            joined_date=getattr(user, 'created_at', None),
        )
    except Exception as e:
        logging.error(f"dispatch_founding_member_email failed for {getattr(user, 'email', '?')}: {e}")
        return False
