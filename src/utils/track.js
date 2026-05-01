import { API_BASE } from '../hooks/useApi';

// Lightweight tracker for Phase 1 bet-tap surfaces. Posts to /api/events
// with sendBeacon (survives navigation) and falls back to keepalive
// fetch. Server normalizes payload, attaches user_id from session if
// present, computes is_internal server-side. Fire-and-forget.
//
// Distinct from src/utils/eventTracker.js: that's a long-lived batched
// tracker for view/session events. track() is single-event, beacon-first,
// for high-intent moments like bet_tap that must survive outbound nav.
export function track(event, props = {}) {
  const body = JSON.stringify({
    event,
    ...props,
    client_ts: new Date().toISOString(),
  });
  const url = `${API_BASE}/events`;
  if (typeof navigator !== 'undefined' && typeof navigator.sendBeacon === 'function') {
    try {
      const blob = new Blob([body], { type: 'text/plain' });
      if (navigator.sendBeacon(url, blob)) return;
    } catch (e) {
      // Fall through to fetch.
    }
  }
  fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body,
    keepalive: true,
  }).catch(() => {});
}
