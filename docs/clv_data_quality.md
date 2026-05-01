# CLV data quality

Notes on known biases in `picks.clv` and `picks.closing_spread` for model
evaluation purposes. Scope is historical resolved picks. Forward-going
captures use the corrected paths described below.

## 1. April 10 formula bug (RESOLVED)

The closing-lines crons for NBA, WNBA, and MLB used the formula
`clv = closing - pick.line` until commit `84f877c` (2026-04-10), which
replaced it with the current picked-side formula. Every pick with
`result IS NOT NULL` and `game_date < 2026-04-10` carried CLV values
computed under the old formula.

**Backfill ran 2026-05-01** (`scripts/backfill_clv_pre_april10.py`). 57
picks examined, 35 updated to current-formula values, 8 unchanged
(formula collisions), 14 skipped (`closing_spread IS NULL`, mostly
Pre-Cal seed picks). Marlins-04-04, Marlins-04-05, and Raptors-04-09
were the production-screenshot rows verified post-backfill. After this
step, every pre-04-10 row that has a non-null `closing_spread` carries a
CLV value computed under the current formula.

## 2. MLB capture-timing — two distinct failure modes

The MLB closing-lines cron captures `mlb_games.spread_home` as the close
on every pass, then writes that value to `picks.closing_spread`. The cron
runs every 1 min from 11 AM to 1 AM ET. Audit of 30 random resolved MLB
picks shows the timing of the **last** capture per game is bimodal:

### Mode A: post-tip contamination (12/30 sampled, 40%)

`close_collected_at` lands AFTER first pitch — lag range 73 to 197 min,
average 135 min. The cron's old filter was `home_score IS NULL`, so
captures continued through the in-progress portion of the game until
ESPN reported scoring. The values captured during that window can
reflect in-game spread movement, not the real close.

The MLB cron filter was tightened on 2026-04-30 (commit `f46ba5d`) to
mirror NBA's behavior — only capture when game_time is in the next 10
minutes AND the game is unscored. **Picks captured after that deploy use
the new filter and are not subject to Mode A.** Historical pre-deploy
MLB rows are NOT retrofitted: `line_snapshots` only writes 3 entries per
day for MLB (collection-only, not the every-1-min closing cron), so
internal data has no late-game line history to recover from.

### Mode B: pre-tip stall, "frozen at noon" (LATENT BUG)

`close_collected_at` stops advancing hours before tip-off even though
the every-1-min cron should keep running until home_score is populated.
Examples from the audit:

| Game | game_time (UTC) | close_collected_at | Lead time |
|---|---|---|---|
| Marlins @ Dodgers 2026-04-29 | 19:11 | 16:30 | 161 min |
| Cleveland @ Dodgers 2026-04-01 | 00:20 (next day) | 16:30 | 469 min |
| Mets @ Giants 2026-04-02 | 01:45 (next day) | 16:30 | 554 min |

These rows have `close_collected_at` matching the noon mlb-collect cron,
suggesting the every-1-min closing-lines cron silently no-oped after
that point. Cause unknown — candidates include premature `home_score`
population from ESPN, API rate limits, or a filter quirk.

**The forward fix does NOT address Mode B.** The 10-min pre-tip window
narrows the eligible capture window but cannot force the cron to
actually run successfully inside that window. If the underlying root
cause is a silent no-op, those captures will still stall.

Mode B is flagged as a separate latent bug requiring its own audit. Not
addressed in the current PR.

## 3. Structural CLV-signal weakness on MLB run lines

MLB run-line spreads are pinned at ±1.5 by market convention. Movement
on the spread itself is rare; almost all sharp action shows up as
movement in the juice (-110 → -120 etc.) or in the alternate run lines,
not in the run line number.

Audit of 34 resolved MLB picks showed 29 (85%) with `clv = 0.0`. After
the April 10 backfill those zeros are mathematically correct under the
current formula given the stored inputs — but the stored `closing_spread`
values themselves are subject to Modes A and B. Even setting those bugs
aside, an 85% zero-CLV rate makes MLB run-line CLV a noisy signal for
discriminating between picks: nearly every pick "matches the close"
because the close almost always equals the entry spread.

**Implication for model eval:** treat MLB run-line CLV averages as a
weak signal. Magnitude differences will be dominated by the small
fraction of picks where the run line actually moved off ±1.5. Do not
use MLB run-line CLV as a primary KPI.

## 4. Cohorts for CLV-based model evaluation

When comparing CLV averages across time periods, subset by sport AND by
the following bug-status cohorts:

| Cohort | Date range | NBA | WNBA | MLB |
|---|---|---|---|---|
| 1. Pre-April-10 (raw) | game_date < 2026-04-10 | n/a (backfilled) | n/a (backfilled) | n/a (backfilled) |
| 2. Pre-April-10 (post-backfill) | game_date < 2026-04-10 | current formula | current formula | current formula + Mode A/B applies |
| 3. April 10 to MLB fix deploy | 2026-04-10 to 2026-04-30 | current formula | current formula | current formula + Mode A/B applies |
| 4. Post-MLB-fix-deploy | game_date >= 2026-04-30 | current formula | current formula | current formula, Mode A resolved, Mode B may persist |
| 5. Post-Mode-B-fix | TBD (latent bug not yet fixed) | n/a | n/a | current formula, Mode A and Mode B both resolved |

**MLB structural caveat applies to all five cohorts.** Run-line CLV is
weak as a signal regardless of bug status.

NBA and WNBA cohorts are clean from cohort 2 onward — no capture-timing
issues observed (NBA cron has had time-window protection throughout;
WNBA has no resolved picks).

## 5. Future work

- **Diagnose Mode B "frozen at noon" cron behavior.** Audit
  `mlb_games.close_collected_at` distribution against scheduled
  `game_time` over a multi-day window. Check ESPN home_score population
  patterns and Odds API error logs around the 12-3 PM ET interval.

- **Track moneyline CLV for MLB.** Run-line CLV is structurally weak;
  moneyline CLV is the meaningful signal for MLB but isn't captured.
  Schema additions: `picks.moneyline_at_pick`, `picks.moneyline_close`,
  derived `picks.moneyline_clv_pct`.

- **Third-party historical line API for retroactive MLB cleanup.** If
  model evaluation ever requires accurate historical MLB closing lines,
  internal `line_snapshots` is insufficient (3/day MLB granularity).
  Candidates: OddsJam historical, Action Network archive, Don Best
  feeds. Cost and coverage TBD.
