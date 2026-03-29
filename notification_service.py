import os
import logging


def _get_push_functions():
    try:
        from app import send_push_to_all, send_push_notification, send_admin_alert
        return send_push_to_all, send_push_notification, send_admin_alert
    except ImportError:
        logging.error("Could not import push functions from app")
        return None, None, None


_TEAM_ABBR = {
    'Atlanta Hawks': 'ATL', 'Boston Celtics': 'BOS', 'Brooklyn Nets': 'BKN',
    'Charlotte Hornets': 'CHA', 'Chicago Bulls': 'CHI', 'Cleveland Cavaliers': 'CLE',
    'Dallas Mavericks': 'DAL', 'Denver Nuggets': 'DEN', 'Detroit Pistons': 'DET',
    'Golden State Warriors': 'GSW', 'Houston Rockets': 'HOU', 'Indiana Pacers': 'IND',
    'Los Angeles Clippers': 'LAC', 'LA Clippers': 'LAC',
    'Los Angeles Lakers': 'LAL', 'LA Lakers': 'LAL',
    'Memphis Grizzlies': 'MEM', 'Miami Heat': 'MIA', 'Milwaukee Bucks': 'MIL',
    'Minnesota Timberwolves': 'MIN', 'New Orleans Pelicans': 'NOP',
    'New York Knicks': 'NYK', 'Oklahoma City Thunder': 'OKC',
    'Orlando Magic': 'ORL', 'Philadelphia 76ers': 'PHI', 'Phoenix Suns': 'PHX',
    'Portland Trail Blazers': 'POR', 'Sacramento Kings': 'SAC',
    'San Antonio Spurs': 'SAS', 'Toronto Raptors': 'TOR',
    'Utah Jazz': 'UTA', 'Washington Wizards': 'WAS',
    'Arizona Diamondbacks': 'ARI', 'Atlanta Braves': 'ATL',
    'Baltimore Orioles': 'BAL', 'Boston Red Sox': 'BOS',
    'Chicago Cubs': 'CHC', 'Chicago White Sox': 'CWS',
    'Cincinnati Reds': 'CIN', 'Cleveland Guardians': 'CLE',
    'Colorado Rockies': 'COL', 'Detroit Tigers': 'DET',
    'Houston Astros': 'HOU', 'Kansas City Royals': 'KC',
    'Los Angeles Angels': 'LAA', 'Los Angeles Dodgers': 'LAD',
    'Miami Marlins': 'MIA', 'Milwaukee Brewers': 'MIL',
    'Minnesota Twins': 'MIN', 'New York Mets': 'NYM', 'New York Yankees': 'NYY',
    'Athletics': 'OAK', 'Oakland Athletics': 'OAK',
    'Philadelphia Phillies': 'PHI', 'Pittsburgh Pirates': 'PIT',
    'San Diego Padres': 'SD', 'San Francisco Giants': 'SF',
    'Seattle Mariners': 'SEA', 'St. Louis Cardinals': 'STL',
    'Tampa Bay Rays': 'TB', 'Texas Rangers': 'TEX',
    'Toronto Blue Jays': 'TOR', 'Washington Nationals': 'WSH',
}


def _abbr(team_name):
    if not team_name:
        return '???'
    return _TEAM_ABBR.get(team_name, team_name.split()[-1][:3].upper())


def send_pick_notification(pick):
    send_push_to_all, _, _ = _get_push_functions()
    if not send_push_to_all:
        return False
    try:
        from sport_config import get_sport_config
        edge = round(pick.edge_pct, 1) if pick.edge_pct is not None else 0
        confidence = pick.model_confidence or 0
        rating = "STRONG" if confidence >= 0.60 else "LEAN"
        sport = getattr(pick, 'sport', 'nba') or 'nba'
        cfg = get_sport_config(sport)
        phase = cfg.get('model_phase', 'deployment')

        if phase == 'calibration':
            sport_tag = cfg.get('name', sport.upper())
            title = f"{rating} {sport_tag} Signal \u00b7 {edge}% Edge"
            body = f"{pick.side} \u00b7 {_abbr(pick.away_team)} @ {_abbr(pick.home_team)} \u00b7 Calibration phase"
        else:
            title = f"{rating} Signal \u00b7 {edge}% Edge"
            body = f"{pick.side} \u00b7 {_abbr(pick.away_team)} @ {_abbr(pick.home_team)} \u00b7 {confidence * 100:.0f}% model confidence"
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
        from sport_config import get_sport_config
        games_analyzed = pass_entry.games_analyzed or 0
        closest_edge = getattr(pass_entry, 'closest_edge_pct', None)
        sport = getattr(pass_entry, 'sport', 'nba') or 'nba'
        cfg = get_sport_config(sport)
        phase = cfg.get('model_phase', 'deployment')
        threshold = cfg.get('edge_threshold_pct', 3.5)

        if phase == 'calibration':
            sport_tag = cfg.get('name', sport.upper())
            title = f"{sport_tag} \u00b7 No Qualifying Edge"
        else:
            title = "No Qualifying Edge"

        if closest_edge and closest_edge > 0:
            body = f"{games_analyzed} games scanned. Closest edge: {closest_edge:.1f}% (threshold: {threshold}%)."
        else:
            body = f"{games_analyzed} games scanned, none above threshold."

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
        away = _abbr(pick.away_team)
        home = _abbr(pick.home_team)

        clv_line = ""
        opening = getattr(pick, 'line', None)
        closing = getattr(pick, 'closing_spread', None)
        if opening is not None and closing is not None and opening != closing:
            clv_line = f" Line moved {opening:+g} to {closing:+g}."

        if result == 'win':
            title = f"Win {pnl_str} \u00b7 {pick.side}"
            body = f"{away} @ {home} covered.{clv_line}"
        elif result == 'loss':
            title = f"Loss {pnl_str} \u00b7 {pick.side}"
            body = f"{away} @ {home} did not cover. Process unchanged."
        else:
            title = f"Push \u00b7 {pick.side}"
            body = f"{away} @ {home} landed on the number. Stake returned."

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
        time_label = f"{minutes_until}m" if minutes_until < 60 else f"{minutes_until // 60}h"
        title = f"{pick.side} \u00b7 {time_label} to tip"

        away = _abbr(pick.away_team)
        home = _abbr(pick.home_team)
        game_time = getattr(pick, 'game_time', '') or ''
        edge = pick.edge_pct if pick.edge_pct is not None else None
        edge_part = f" Edge holds at {edge:.1f}%." if edge else ""
        time_part = f" {game_time}." if game_time else ""
        body = f"{away} @ {home} \u00b7{time_part}{edge_part}"

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
        units = stats.get('units', 0)
        total_picks = wins + losses

        if total_picks == 0:
            title = f"Week {week_num} \u00b7 All Pass"
            body = f"7 slates scanned, 0 qualifying edges."
        else:
            units_str = f"+{units:.1f}u" if units >= 0 else f"{units:.1f}u"
            title = f"Week {week_num} \u00b7 {wins}-{losses} \u00b7 {units_str}"
            body = f"{total_picks} {'pick' if total_picks == 1 else 'picks'}, {pass_days} pass days. {roi:+.1f}% ROI."

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
        from sport_config import get_sport_config
        sport = getattr(pick, 'sport', 'nba') or 'nba'
        cfg = get_sport_config(sport)
        threshold = cfg.get('edge_threshold_pct', 3.5)
        away = _abbr(pick.away_team)
        home = _abbr(pick.home_team)

        title = f"Pick Withdrawn \u00b7 {pick.side}"
        body = f"{away} @ {home} \u00b7 edge dropped below {threshold}% threshold before tip."
        data = {'type': 'revoke', 'pick_id': str(pick.id)}
        sent = send_push_to_all(title, body, data=data, premium_only=True, notification_type='revoke')
        logging.info(f"Revoke notification sent to {sent} device(s)")
        return sent > 0
    except Exception as e:
        logging.error(f"Revoke notification failed: {e}")
        return False


def send_market_scan_push(report):
    """Send morning market scan push after run-model. report = build_market_report_dict(...)."""
    send_push_to_all, _, _ = _get_push_functions()
    if not send_push_to_all or not report.get('available'):
        return False
    try:
        title = "Market Scan Complete"
        edges = report.get('edges_detected', 0)
        top = report.get('largest_edge')
        markets = report.get('games_analyzed', 0)
        if edges == 0:
            body = f"{markets} games scanned, no qualifying edge."
        else:
            if top is not None and top > 0:
                body = f"{edges} edge{'s' if edges != 1 else ''} detected. Top edge +{top:.0f}%."
            else:
                body = f"{markets} games scanned, {edges} edge{'s' if edges != 1 else ''} detected."
        data = {'type': 'market_scan', 'date': report.get('date', ''), 'deep_link': '/market'}
        sent = send_push_to_all(title, body, data=data, premium_only=True, notification_type='market_scan')
        logging.info(f"Market scan push sent to {sent} device(s)")
        return sent > 0
    except Exception as e:
        logging.error(f"Market scan push failed: {e}")
        return False


def send_market_note_notification(insight):
    """Notify users when a new Market Note is published."""
    send_push_to_all, _, _ = _get_push_functions()
    if not send_push_to_all:
        return False
    try:
        title = "New Market Note"
        body = (insight.title or insight.excerpt or '')[:80]
        data = {'type': 'market_note', 'insight_id': str(insight.id), 'slug': insight.slug or '', 'deep_link': f'/insights/{insight.slug or ""}'}
        sent = send_push_to_all(title, body, data=data, premium_only=True, notification_type='market_note')
        logging.info(f"Market note notification sent to {sent} device(s)")
        return sent > 0
    except Exception as e:
        logging.error(f"Market note notification failed: {e}")
        return False


def send_journal_notification(insight):
    """Notify users when a new journal article is published."""
    send_push_to_all, _, _ = _get_push_functions()
    if not send_push_to_all:
        return False
    try:
        title = "New Insight"
        body = (insight.title or '')[:80]
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
        title = "Trial Expires Tomorrow"
        body = "Your SharpPicks trial ends tomorrow. Lock in your subscription."
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
