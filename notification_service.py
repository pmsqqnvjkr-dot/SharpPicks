import os
import logging


def _get_push_functions():
    try:
        from app import send_push_to_all, send_push_notification, send_admin_alert
        return send_push_to_all, send_push_notification, send_admin_alert
    except ImportError:
        logging.error("Could not import push functions from app")
        return None, None, None


def send_pick_notification(pick):
    send_push_to_all, _, _ = _get_push_functions()
    if not send_push_to_all:
        return False
    try:
        title = 'SharpPicks \u2014 Qualified Edge'
        body = f'Edge identified. {pick.away_team} @ {pick.home_team}. View in app.'
        data = {'type': 'pick', 'pick_id': str(pick.id)}
        sent = send_push_to_all(title, body, data=data, premium_only=True)
        logging.info(f"Pick notification sent to {sent} device(s)")
        return sent > 0
    except Exception as e:
        logging.error(f"Pick notification failed: {e}")
        return False


def send_pass_notification(pass_entry):
    send_push_to_all, _, _ = _get_push_functions()
    if not send_push_to_all:
        return False
    try:
        title = 'SharpPicks \u2014 No Action'
        body = f'{pass_entry.games_analyzed} games analyzed. No edge detected.'
        data = {'type': 'pass', 'date': str(pass_entry.date)}
        sent = send_push_to_all(title, body, data=data, premium_only=True)
        logging.info(f"Pass notification sent to {sent} device(s)")
        return sent > 0
    except Exception as e:
        logging.error(f"Pass notification failed: {e}")
        return False


def send_result_notification(pick, result):
    send_push_to_all, _, _ = _get_push_functions()
    if not send_push_to_all:
        return False
    try:
        if result == 'win':
            body = f'Result: WIN. {pick.side} covered.'
        elif result == 'loss':
            body = f'Result: LOSS. {pick.side} did not cover.'
        else:
            body = 'Result: PUSH. No impact.'
        title = 'SharpPicks \u2014 Result'
        data = {'type': 'result', 'pick_id': str(pick.id), 'result': result}
        sent = send_push_to_all(title, body, data=data, premium_only=True)
        logging.info(f"Result notification ({result}) sent to {sent} device(s)")
        return sent > 0
    except Exception as e:
        logging.error(f"Result notification failed: {e}")
        return False


def send_weekly_summary_notification(stats):
    send_push_to_all, _, _ = _get_push_functions()
    if not send_push_to_all:
        return False
    try:
        record = f"{stats.get('wins', 0)}W\u2013{stats.get('losses', 0)}L"
        passes = stats.get('passes', 0)
        title = 'SharpPicks \u2014 Weekly Report'
        body = f'{record}. {passes} pass days. Full report in app.'
        data = {'type': 'weekly_summary'}
        sent = send_push_to_all(title, body, data=data, premium_only=True)
        logging.info(f"Weekly summary notification sent to {sent} device(s)")
        return sent > 0
    except Exception as e:
        logging.error(f"Weekly summary notification failed: {e}")
        return False


def send_revoke_notification(pick, reason):
    send_push_to_all, _, _ = _get_push_functions()
    if not send_push_to_all:
        return False
    try:
        title = 'SharpPicks \u2014 Update'
        body = f'{pick.away_team} @ {pick.home_team} withdrawn. Threshold no longer met.'
        data = {'type': 'revoke', 'pick_id': str(pick.id)}
        sent = send_push_to_all(title, body, data=data, premium_only=True)
        logging.info(f"Revoke notification sent to {sent} device(s)")
        return sent > 0
    except Exception as e:
        logging.error(f"Revoke notification failed: {e}")
        return False


def send_admin_health_alert(title, details):
    _, _, send_admin_alert = _get_push_functions()
    if not send_admin_alert:
        return False
    try:
        sent = send_admin_alert(title, details)
        return sent > 0
    except Exception as e:
        logging.error(f"Admin health alert failed: {e}")
        return False
