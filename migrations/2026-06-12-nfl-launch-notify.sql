-- Track which users opted in to a one-shot "NFL launched" push notification
-- from the NFL Calibration screen's "Notify me" card. The button is a one-tap
-- intent capture: when nfl.launched flips to true in config/launch_config.json,
-- a one-off broadcast goes to every user with nfl_launch_notify = true and
-- then this column has no further read path.
--
-- Default false so existing rows are correct as-is. The flip endpoint is
-- POST /api/account/nfl-launch-notify (auth required) and only sets true
-- (never false; this is a one-way opt-in). User_events row is logged in
-- parallel with surface='nfl_calibration' for the funnel tile.
--
-- No index: the column is only read once, at launch broadcast time, by an
-- offline script that scans the table once. Indexing for a one-shot query
-- would waste write amplification on every login.

BEGIN;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS nfl_launch_notify BOOLEAN NOT NULL DEFAULT false;

COMMIT;
