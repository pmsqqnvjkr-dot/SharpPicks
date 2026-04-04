# Sharp Picks — Cron Job Schedule (cron-job.org)

All times **Eastern (ET)**. Use `X-Cron-Secret` header with your `CRON_SECRET` value.

## Pipeline Order (Critical)
1. **run_model?force=true** runs NBA collect + MLB collect + NBA model (does **not** run MLB model — that has its own schedule)
2. **mlb-run-model?force=true** runs the MLB model independently at 11:00 AM
3. **grade_picks** runs **after** games finish (overnight + late West Coast) — grades all sports
4. **mlb-grade** grades MLB picks specifically from ESPN scores

## Recommended Schedule

| Job | URL | Schedule (ET) |
|-----|-----|---------------|
| run_model | `https://app.sharppicks.ai/api/cron/run-model?force=true` | 10:15 AM, 2:15 PM |
| refresh_lines | `https://app.sharppicks.ai/api/cron/refresh-lines` | Every 10 min, 6 AM–2 AM |
| closing_lines | `https://app.sharppicks.ai/api/cron/closing-lines` | Every 1 min, 10 AM–1 AM |
| grade_picks | `https://app.sharppicks.ai/api/cron/grade-picks` | 3:45 AM, 11:30 AM |
| grade_whatifs | `https://app.sharppicks.ai/api/cron/grade-whatifs` | 4:05 AM, 4:05 PM |
| pretip_validate | `https://app.sharppicks.ai/api/cron/pretip-validate` | 9:55 AM, 4:55 PM |
| backup | `https://app.sharppicks.ai/api/cron/backup` | 3:20 AM daily |
| data_quality | `https://app.sharppicks.ai/api/cron/check-data-quality` | 4:15 AM, 12:15 PM |
| expire_trials | `https://app.sharppicks.ai/api/cron/expire-trials` | Hourly at :10 |
| weekly_summary | `https://app.sharppicks.ai/api/cron/weekly-summary` | Mon 6:30 AM |
| model_watchdog | `https://app.sharppicks.ai/api/cron/model-watchdog` | 10:45 AM, 11:30 AM, 12:30 PM |
| admin_alert | `https://app.sharppicks.ai/api/cron/admin-alert` | Every 2–4 hours (sends push to admins when issues detected) |

### MLB-Specific Jobs

| Job | URL | Schedule (ET) |
|-----|-----|---------------|
| mlb_collect | `https://app.sharppicks.ai/api/cron/mlb-collect` | 9:00 AM, 12:00 PM |
| mlb_run_model | `https://app.sharppicks.ai/api/cron/mlb-run-model?force=true` | 11:00 AM |
| mlb_closing_lines | `https://app.sharppicks.ai/api/cron/mlb-closing-lines` | Every 1 min, 11 AM–1 AM |
| mlb_grade | `https://app.sharppicks.ai/api/cron/mlb-grade` | 3:30 AM, 11:00 AM |

> **Note:** `run-model?force=true` at 10:15 AM collects MLB game data but does NOT run the MLB model. The MLB model runs independently at 11:00 AM via `mlb-run-model`. This prevents the two sports from interfering with each other.

## How NBA and MLB stay separated
- **10:15 AM** — `run-model?force=true` collects NBA games + MLB games, then runs **only the NBA model**
- **11:00 AM** — `mlb-run-model?force=true` runs **only the MLB model** (data already collected at 10:15)
- **Closing lines** — NBA uses `closing-lines` (queries `games` table), MLB uses `mlb-closing-lines` (queries `mlb_games` table)
- **Grading** — `grade-picks` grades all pending picks across sports; `mlb-grade` is MLB-specific (harmless overlap)
- Each sport has its own throttle keys (`run_model` vs `mlb_run_model`) and cron locks, so they never block each other

## Throttling
- run_model, collect_games: 10 min min interval (skip if run again within 10 min)
- force=true bypasses throttle
