import os
import logging
import requests


ONESIGNAL_APP_ID = os.environ.get('ONESIGNAL_APP_ID', '')
ONESIGNAL_API_KEY = os.environ.get('ONESIGNAL_API_KEY', '')

ONESIGNAL_API_URL = 'https://onesignal.com/api/v1/notifications'


def _send_notification(headings, contents, segment=None, filters=None, data=None):
    if not ONESIGNAL_APP_ID or not ONESIGNAL_API_KEY:
        logging.warning("OneSignal not configured. Notification not sent.")
        return False
    
    payload = {
        'app_id': ONESIGNAL_APP_ID,
        'headings': {'en': headings},
        'contents': {'en': contents},
    }
    
    if segment:
        payload['included_segments'] = [segment]
    if filters:
        payload['filters'] = filters
    if data:
        payload['data'] = data
    
    headers = {
        'Authorization': f'Basic {ONESIGNAL_API_KEY}',
        'Content-Type': 'application/json',
    }
    
    try:
        resp = requests.post(ONESIGNAL_API_URL, json=payload, headers=headers, timeout=10)
        if resp.status_code in (200, 201):
            logging.info(f"Push notification sent: {headings}")
            return True
        else:
            logging.error(f"OneSignal error {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        logging.error(f"Push notification failed: {e}")
        return False


def send_pick_notification(pick):
    return _send_notification(
        headings='Sharp Picks',
        contents=f'Qualified opportunity posted. {pick.away_team} @ {pick.home_team}.',
        segment='Pro Users',
        data={'type': 'pick', 'pick_id': pick.id},
    )


def send_pass_notification(pass_entry):
    return _send_notification(
        headings='Sharp Picks — No Action Today',
        contents=f'{pass_entry.games_analyzed} games analyzed. No edge detected. Discipline is the edge.',
        segment='Pass Alerts',
        data={'type': 'pass', 'date': pass_entry.date},
    )


def send_result_notification(pick, result):
    if result == 'win':
        contents = f'Result: WIN. {pick.side} covered. Your discipline paid off.'
    elif result == 'loss':
        contents = f'Result: LOSS. {pick.side} did not cover. The edge plays out over time.'
    else:
        contents = f'Result: PUSH. {pick.side} pushed. No action needed.'
    
    return _send_notification(
        headings='Sharp Picks — Result',
        contents=contents,
        segment='Pro Users',
        data={'type': 'result', 'pick_id': pick.id, 'result': result},
    )
