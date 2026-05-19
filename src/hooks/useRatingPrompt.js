import { useCallback, useEffect, useRef, useState } from 'react';
import { Capacitor } from '@capacitor/core';
import { apiGet, apiPost } from './useApi';

// Orchestrates the Android rating prompt:
//
//   1. After a natural-pause delay, ping the backend for eligibility.
//   2. If eligible AND platform=android AND user is authenticated, open
//      the RatingPrompt modal (parent component handles render).
//   3. On positive tap, call @capacitor-community/in-app-review.
//
// All gating state (cooldowns, has_rated_via_flow, recent_loss) lives
// in user_events server-side — this hook just asks "can we show now?"
//
// iOS is hard-gated off. Web is hard-gated off. Internal testers and
// Stripe Connect / fraud-flow paths are filtered server-side via the
// eligibility endpoint.

const NATURAL_PAUSE_DELAY_MS = 10_000;
const ELIGIBILITY_CHECK_KEY = 'sp_rating_prompt_checked_at';
const ELIGIBILITY_CHECK_THROTTLE_MS = 24 * 60 * 60 * 1000;

export default function useRatingPrompt({ enabled = true, user = null } = {}) {
  const [open, setOpen] = useState(false);
  const evaluatedRef = useRef(false);

  const platform = (typeof Capacitor !== 'undefined' && Capacitor.getPlatform)
    ? Capacitor.getPlatform()
    : 'web';

  const triggerNativeReview = useCallback(async () => {
    if (platform !== 'android') return;
    try {
      const mod = await import('@capacitor-community/in-app-review');
      const InAppReview = mod.InAppReview || mod.default?.InAppReview || mod.default;
      if (!InAppReview || typeof InAppReview.requestReview !== 'function') {
        return;
      }
      await InAppReview.requestReview();
      try {
        apiPost('/rating-prompt/event', { event: 'google_api_triggered' });
      } catch {
        // best-effort
      }
    } catch (err) {
      // Google rate-limits and silently no-ops in internal testing.
      // We've already logged tapped_positive server-side; nothing else
      // to do on failure.
      try {
        apiPost('/rating-prompt/event', {
          event: 'google_api_triggered',
          data: { error: String(err).slice(0, 200) },
        });
      } catch {
        // best-effort
      }
    }
  }, [platform]);

  useEffect(() => {
    if (!enabled || evaluatedRef.current) return;
    if (platform !== 'android') return;
    if (!user) return;

    // Light client-side throttle so we don't ping the eligibility
    // endpoint on every app open (server still authoritative).
    try {
      const last = parseInt(window.localStorage.getItem(ELIGIBILITY_CHECK_KEY) || '0', 10);
      if (last && Date.now() - last < ELIGIBILITY_CHECK_THROTTLE_MS) return;
    } catch {
      // localStorage unavailable; proceed anyway
    }

    evaluatedRef.current = true;
    const timer = setTimeout(async () => {
      try {
        const res = await apiGet('/rating-prompt/eligibility');
        if (res?.eligible) {
          setOpen(true);
        }
        try {
          window.localStorage.setItem(ELIGIBILITY_CHECK_KEY, String(Date.now()));
        } catch {
          // ignore
        }
      } catch {
        // network failure or auth issue; silent
      }
    }, NATURAL_PAUSE_DELAY_MS);

    return () => clearTimeout(timer);
  }, [enabled, platform, user]);

  return {
    open,
    onPositive: triggerNativeReview,
    onClose: () => setOpen(false),
  };
}
