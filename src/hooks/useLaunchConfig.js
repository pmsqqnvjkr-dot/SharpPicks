import { useEffect, useState } from 'react';
import { Capacitor } from '@capacitor/core';

// useLaunchConfig: fetches /api/public/launch-config once per session
// (with a periodic refresh) and returns the parsed JSON. Used by
// AppHeader for sport-chip state dots, PicksTab + screen selector for
// the special empty-state short-circuit, and the landing desk strip.
//
// Returns { config, loading, error }.
//   config:  the parsed JSON, or null if not yet loaded / failed.
//   loading: true on the first fetch only; subsequent refreshes do not
//            flip this back to true. Treat null config + loading=false
//            as "fetch failed, assume defaults" (the resolver helper
//            returns null which means fall through to existing logic).
//   error:   the most recent fetch error message, or null.
//
// Cache is module-scoped so the first hook caller pays the fetch cost
// and every subsequent caller (across the app) gets the cached object.
// REFRESH_MS controls how often the background refresh fires.

const PROD_URL = 'https://app.sharppicks.ai';
const API_BASE = Capacitor.isNativePlatform() ? PROD_URL : '';
const REFRESH_MS = 60 * 60 * 1000;

let cachedConfig = null;
let cachedAt = 0;
let inFlight = null;
const subscribers = new Set();

async function fetchConfig() {
  if (inFlight) return inFlight;
  inFlight = (async () => {
    try {
      const res = await fetch(`${API_BASE}/api/public/launch-config`, {
        credentials: 'include',
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      cachedConfig = data;
      cachedAt = Date.now();
      subscribers.forEach((cb) => cb(data, null));
      return data;
    } catch (e) {
      const msg = e?.message || String(e);
      subscribers.forEach((cb) => cb(cachedConfig, msg));
      throw e;
    } finally {
      inFlight = null;
    }
  })();
  return inFlight;
}

export function useLaunchConfig() {
  const [config, setConfig] = useState(cachedConfig);
  const [loading, setLoading] = useState(cachedConfig === null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;
    const cb = (data, err) => {
      if (!mounted) return;
      if (data) setConfig(data);
      setError(err);
    };
    subscribers.add(cb);

    const needFetch = cachedConfig === null || (Date.now() - cachedAt) > REFRESH_MS;
    if (needFetch) {
      fetchConfig()
        .catch(() => { /* swallow; cb already received error */ })
        .finally(() => { if (mounted) setLoading(false); });
    } else {
      setLoading(false);
    }

    return () => {
      mounted = false;
      subscribers.delete(cb);
    };
  }, []);

  return { config, loading, error };
}

// Read-only helper for non-React surfaces that just want the last-known
// config snapshot without subscribing. Returns null if nothing has been
// fetched yet.
export function getCachedLaunchConfig() {
  return cachedConfig;
}
