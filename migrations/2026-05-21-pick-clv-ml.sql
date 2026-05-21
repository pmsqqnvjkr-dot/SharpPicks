-- Moneyline CLV columns on Pick.
--
-- Spread CLV (clv column) reads ~0 across MLB picks because run lines
-- are structurally fixed at +/-1.5 — they almost never drift the way
-- NBA spreads do. The real MLB sharp-money signal lives in moneyline
-- movement, which is continuous.
--
-- closing_ml: closing moneyline for the side the pick was on, American
--             odds. Used both for display and as the input to clv_ml.
-- clv_ml:     moneyline CLV in implied-probability percentage points.
--             Computed as (closing_implied - entry_implied) * 100.
--             Positive = market shifted toward our pick after entry.
--             See utils/clv.py clv_ml_prob.
--
-- See app.py /api/cron/backfill-mlb-clv for backfill of historical picks
-- and the closing-lines crons (NBA, WNBA, MLB) for ongoing capture.

ALTER TABLE picks ADD COLUMN IF NOT EXISTS closing_ml INTEGER NULL;
ALTER TABLE picks ADD COLUMN IF NOT EXISTS clv_ml DOUBLE PRECISION NULL;

-- Helpful for the public stats endpoint aggregation.
CREATE INDEX IF NOT EXISTS idx_picks_sport_clv_ml ON picks (sport, clv_ml)
  WHERE clv_ml IS NOT NULL;
