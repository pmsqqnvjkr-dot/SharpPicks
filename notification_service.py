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
        confidence = pick.model_confidence or 0
        rating = "STRONG" if confidence >= 0.60 else "LEAN"

        title = f"{rating} Pick — {edge}% Edge"
        body = f"{pick.side} ({pick.away_team} @ {pick.home_team}). Model confidence: {confidence * 100:.0f}%. Tap for full analysis."
        data = {'type': 'pick', 'pick_id': str(pick.id)}
        sent = send_push_to_all(title, body, data=data, premium_only=True, notification_type='pick')
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
        closest_edge = getattr(pass_entry, 'closest_edge_pct', None)

        title = "Pass Day — No Qualifying Edge"
        if closest_edge and closest_edge > 0:
            body = f"{games_analyzed} games analyzed. Closest edge: {closest_edge:.1f}% (need 3%+). Restraint is the edge."
        else:
            body = f"{games_analyzed} games analyzed, none above threshold. Capital preserved for a better spot."
        data = {'type': 'pass', 'date': str(pass_entry.date)}
        sent = send_push_to_all(title, body, data=data, premium_only=True, notification_type='pass')
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
        pnl = pick.profit_units
        pnl_str = f"+{pnl:.2f}u" if pnl and pnl > 0 else f"{pnl:.2f}u" if pnl else ""

        if result == 'win':
            title = f"Win {pnl_str} — {pick.side}"
            body = f"{pick.away_team} @ {pick.home_team} covered. The edge was real. Same process tomorrow."
        elif result == 'loss':
            title = f"Loss {pnl_str} — {pick.side}"
            body = f"{pick.away_team} @ {pick.home_team} didn't cover. Variance, not a broken process. No adjustments needed."
        else:
            title = f"Push — {pick.side}"
            body = f"{pick.away_team} @ {pick.home_team} landed on the number. Stake returned. On to the next."

        data = {'type': 'result', 'pick_id': str(pick.id), 'result': result}
        sent = send_push_to_all(title, body, data=data, premium_only=True, notification_type='result')
        logging.info(f"Result notification ({result}) sent to {sent} device(s)")
        return sent > 0
    except Exception as e:
        logging.error(f"Result notification failed: {e}")
        return False


def send_pretip_reminder(pick, minutes_until=60):
    send_push_to_all, _, _ = _get_push_functions()
    if not send_push_to_all:
        return False
    try:
        time_label = f"{minutes_until} min" if minutes_until < 60 else f"{minutes_until // 60}h"
        title = f"Tip-off in {time_label}"
        body = f"{pick.side} — {pick.away_team} @ {pick.home_team}. Make sure your bet is placed."
        data = {'type': 'pretip', 'pick_id': str(pick.id)}
        sent = send_push_to_all(title, body, data=data, premium_only=True, notification_type='pretip')
        logging.info(f"Pre-tip reminder sent to {sent} device(s)")
        return sent > 0
    except Exception as e:
        logging.error(f"Pre-tip reminder failed: {e}")
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
        pass_days = stats.get('passes', 0)
        total_picks = wins + losses

        title = f"Week {week_num} Recap"

        if total_picks == 0:
            body = f"Zero picks, full restraint. {pass_days} pass days — capital preserved for the week ahead."
        elif wins > 0 and losses == 0:
            body = f"Clean {wins}-0 week ({roi:+.1f}% ROI). {pass_days} pass days. The process held."
        elif losses > 0 and wins == 0:
            body = f"Tough 0-{losses} week. Variance within parameters. {pass_days} pass days of discipline still count."
        else:
            body = f"{wins}W-{losses}L ({roi:+.1f}% ROI). Acted on {total_picks} of 7 slates. Tap for the full narrative."

        data = {'type': 'weekly_summary'}
        sent = send_push_to_all(title, body, data=data, premium_only=True, notification_type='weekly_summary')
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
        sent = send_push_to_all(title, body, data=data, premium_only=True, notification_type='revoke')
        logging.info(f"Revoke notification sent to {sent} device(s)")
        return sent > 0
    except Exception as e:
        logging.error(f"Revoke notification failed: {e}")
        return False


def send_journal_notification(insight):
    """Notify users when a new journal article is published."""
    send_push_to_all, _, _ = _get_push_functions()
    if not send_push_to_all:
        return False
    try:
        title = "New Journal Entry"
        excerpt = (insight.excerpt or insight.title or '')[:80]
        body = f"{insight.title}" if insight.title else excerpt
        data = {'type': 'journal', 'insight_id': str(insight.id), 'slug': insight.slug or ''}
        sent = send_push_to_all(title, body, data=data, premium_only=True, notification_type='journal')
        logging.info(f"Journal notification sent to {sent} device(s)")
        return sent > 0
    except Exception as e:
        logging.error(f"Journal notification failed: {e}")
        return False


def send_trial_expiring_notification(user, days_remaining):
    """Notify a specific user that their trial is expiring."""
    _, send_push_notification, _ = _get_push_functions()
    if not send_push_notification:
        return False
    try:
        if days_remaining == 1:
            title = "Trial Expires Tomorrow"
            body = "Your Sharp Picks trial ends tomorrow. Subscribe to keep getting picks."
        else:
            title = f"Trial Expires in {days_remaining} Days"
            body = f"Your Sharp Picks trial ends in {days_remaining} days. Lock in your subscription."
        data = {'type': 'trial_expiring', 'days_remaining': str(days_remaining)}
        sent = send_push_notification(user.id, title, body, data)
        logging.info(f"Trial expiring notification sent to user {user.id} ({days_remaining}d)")
        return sent > 0
    except Exception as e:
        logging.error(f"Trial expiring notification failed: {e}")
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
