-- Phase 2.1: metrics_cache table for server-side caching of third-party
-- analytics fetches (Cloudflare, Stripe, GA4, GSC, RevenueCat).
--
-- Browser never talks to those APIs directly: get_or_fetch() in
-- services/metrics_cache.py either returns a fresh cached payload or
-- calls fetch_fn() and writes the result here. last_error preserves
-- a failure reason without overwriting the previously good payload.

CREATE TABLE IF NOT EXISTS metrics_cache (
  cache_key  TEXT PRIMARY KEY,
  payload    JSONB NOT NULL,
  fetched_at TIMESTAMPTZ NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  source     TEXT NOT NULL,
  last_error TEXT
);

CREATE INDEX IF NOT EXISTS metrics_cache_expires_at_idx ON metrics_cache (expires_at);
CREATE INDEX IF NOT EXISTS metrics_cache_source_idx     ON metrics_cache (source);
