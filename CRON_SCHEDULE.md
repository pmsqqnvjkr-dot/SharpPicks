# Sharp Picks — Cron Job Schedule (cron-job.org)

All times **Eastern (ET)**. Use `X-Cron-Secret` header with your `CRON_SECRET` value.

## Pipeline Order (Critical)
1. **Collect games** runs first (5:05 AM) to seed the database
2. **update-ratings** refreshes NBA team ratings (8:30 AM)
3. **run-model?force=true** collects fresh data + runs NBA model (9:00 AM)
4. **mlb-run-model?force=true** collects fresh MLB data + runs MLB model (11:00 AM)
5. **model-watchdog** catches silent failures (9:30 AM, 11:30 AM, 12:30 PM)
6. **grade-picks** runs after games finish (overnight + midday)

## Recommended Schedule

| Job | URL | Schedule (ET) |
|-----|-----|---------------|
| collect_games | `https://app.sharppicks.ai/api/cron/collect-games` | 5:05 AM |
| update_ratings | `https://app.sharppicks.ai/api/cron/update-ratings` | 8:30 AM |
| **run_model** | **`https://app.sharppicks.ai/api/cron/run-model?force=true`** | **9:00 AM**, 2:15 PM |
| refresh_lines | `https://app.sharppicks.ai/api/cron/refresh-lines` | Every 10 min, 10 AM–2 AM |
| closing_lines | `https://app.sharppicks.ai/api/cron/closing-lines` | Every 2 min, 10 AM–1 AM |
| live_scores | `https://app.sharppicks.ai/api/cron/live-scores` | Every 5 min, 10 AM–2 AM |
| grade_picks | `https://app.sharppicks.ai/api/cron/grade-picks` | 3:45 AM, 11:30 AM |
| grade_whatifs | `https://app.sharppicks.ai/api/cron/grade-whatifs` | 4:05 AM, 4:05 PM |
| pretip_validate | `https://app.sharppicks.ai/api/cron/pretip-validate` | 9:55 AM, 4:55 PM |
| model_watchdog | `https://app.sharppicks.ai/api/cron/model-watchdog` | 9:30 AM, 11:30 AM, 12:30 PM |
| backup | `https://app.sharppicks.ai/api/cron/backup` | 3:20 AM daily |
| data_quality | `https://app.sharppicks.ai/api/cron/check-data-quality` | 4:15 AM, 12:15 PM |
| expire_trials | `https://app.sharppicks.ai/api/cron/expire-trials` | Hourly at :10 |
| weekly_summary | `https://app.sharppicks.ai/api/cron/weekly-summary` | Mon 6:30 AM |
| admin_alert | `https://app.sharppicks.ai/api/cron/admin-alert` | Every 4 hours |
| player_props | `https://app.sharppicks.ai/api/cron/player-props` | 4:00 PM, 10:00 PM |
| player_impact | `https://app.sharppicks.ai/api/cron/refresh-player-impact` | 12:00 PM |
| mrr_snapshot | `https://app.sharppicks.ai/api/cron/mrr-snapshot` | 2:00 AM |
| weekly_card | `https://app.sharppicks.ai/api/cron/generate-weekly-card` | Mon 8:00 AM |
| cleanup_events | `https://app.sharppicks.ai/api/cron/cleanup-events` | Sun 8:00 AM |

### MLB-Specific Jobs

| Job | URL | Schedule (ET) |
|-----|-----|---------------|
| mlb_collect | `https://app.sharppicks.ai/api/cron/mlb-collect` | 9:00 AM, 9:30 AM, 12:00 PM |
| **mlb_run_model** | **`https://app.sharppicks.ai/api/cron/mlb-run-model?force=true`** | **11:00 AM** |
| mlb_closing_lines | `https://app.sharppicks.ai/api/cron/mlb-closing-lines` | Every 1 min, 11 AM–1 AM |
| mlb_grade | `https://app.sharppicks.ai/api/cron/mlb-grade` | 3:30 AM, 11:00 AM, 12:04 PM |
| mlb_retrain | `https://app.sharppicks.ai/api/cron/mlb-retrain` | Sun 12:00 PM |
| mlb_validate | `https://app.sharppicks.ai/api/cron/mlb-validate` | 10:30 AM |
| retrain_model | `https://app.sharppicks.ai/api/cron/retrain-model` | Sun 7:00 AM |

> **CRITICAL:** `run-model` and `mlb-run-model` MUST use `?force=true`. Without it, no data is collected before the model runs, stale passes aren't cleared, and the run can silently no-op.

## How NBA and MLB stay separated
- **9:00 AM** — `run-model?force=true` collects NBA + MLB games, then runs **only the NBA model**
- **11:00 AM** — `mlb-run-model?force=true` re-collects MLB data, then runs **only the MLB model**
- **Closing lines** — NBA uses `closing-lines` (queries `games` table), MLB uses `mlb-closing-lines` (queries `mlb_games` table)
- **Grading** — `grade-picks` grades all pending picks across sports; `mlb-grade` is MLB-specific (harmless overlap)
- Each sport has its own throttle keys (`run_model` vs `mlb_run_model`) and cron locks, so they never block each other

## Throttling
- run_model, collect_games: 10 min min interval (skip if run again within 10 min)
- force=true bypasses throttle

## Failure Safety
- `model-watchdog` runs synchronously (not async) and catches silent failures from daemon thread kills on Railway restarts
- Three watchdog runs per day provide coverage: 9:30 AM (NBA), 11:30 AM (NBA+MLB), 12:30 PM (all)
- Watchdog NBA threshold: 9 AM ET, MLB threshold: 11 AM ET
