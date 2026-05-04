-- Phase 3.7: per-request timing table for the admin Infra tab.
--
-- Each row = one HTTP request the Flask app served. After-request
-- middleware writes here for every request whose path doesn't start
-- with /static (we skip CSS/JS asset hits, which would dominate
-- volume without telling us anything useful about app health).
--
-- Indexes:
--   - created_at    : range scans for "last 7 days p95"
--   - status        : count of 5xx in last 24h
--   - path          : per-endpoint breakdowns later
--
-- Storage cost: at ~10 req/s sustained that's ~864K rows/day. A 14-day
-- retention is ~12M rows, ~1.5 GB. Acceptable for now; add a daily
-- cleanup cron if it grows past 30d worth.

BEGIN;

CREATE TABLE IF NOT EXISTS request_metrics (
    id          SERIAL PRIMARY KEY,
    path        VARCHAR(200) NOT NULL,
    method      VARCHAR(10) NOT NULL,
    status      INTEGER NOT NULL,
    duration_ms INTEGER NOT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_request_metrics_created_at ON request_metrics (created_at);
CREATE INDEX IF NOT EXISTS ix_request_metrics_status     ON request_metrics (status);
CREATE INDEX IF NOT EXISTS ix_request_metrics_path       ON request_metrics (path);

COMMIT;
