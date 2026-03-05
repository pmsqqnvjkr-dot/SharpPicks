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
        edge = round(pick.edge_pct, 1) if pick.edge_pct is not None else 0
        spread = f" {pick.line:+.1f}" if pick.line is not None else ""
        title = f"Sharp Pick — {edge}% Edge"
        body = f"{pick.away_team} @ {pick.home_team} · {pick.side}{spread} · Tap to view details"
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
        games_analyzed = pass_entry.games_analyzed or 0
        title = "No Action Today"
        body = f"{games_analyzed} games analyzed, none cleared the threshold. Bankroll protected."
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
            title = f"✓ WIN — {pick.side}"
            body = f"{pick.away_team} @ {pick.home_team} covered. +1u added to record."
        elif result == 'loss':
            title = f"✗ LOSS — {pick.side}"
            body = f"{pick.away_team} @ {pick.home_team} did not cover. Process was sound."
        else:
            title = "PUSH — No Impact"
            body = f"{pick.away_team} @ {pick.home_team}. Stake returned, record unchanged."
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
        week_num = stats.get('week_num', 0)
        wins = stats.get('wins', 0)
        losses = stats.get('losses', 0)
        roi = stats.get('roi', 0)
        top_edge = stats.get('top_edge', 0)
        pass_days = stats.get('passes', 0)
        title = f"Week {week_num} — {wins}W {losses}L"
        body = f"ROI: {roi}% · Best edge: {top_edge}% · {pass_days} pass days"
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
        title = "Pick Withdrawn"
        body = f"{pick.away_team} @ {pick.home_team} — edge dropped below threshold before tip."
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
