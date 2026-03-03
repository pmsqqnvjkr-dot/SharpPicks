# Sharp Picks — Cron Job Schedule (cron-job.org)

All times **Eastern (ET)**. Use `X-Cron-Secret` header with your `CRON_SECRET` value.

## Pipeline Order (Critical)
1. **collect_games** must run **before** run_model
2. **grade_picks** runs **after** games finish (overnight + late West Coast)

## Recommended Schedule

| Job | URL | Schedule (ET) |
|-----|-----|---------------|
| collect_games | `https://app.sharppicks.ai/api/cron/collect-games` | 5:05 AM, 9:00 AM, 1:05 PM |
| run_model | `https://app.sharppicks.ai/api/cron/run-model` | 10:15 AM, 2:15 PM |
| refresh_lines | `https://app.sharppicks.ai/api/cron/refresh-lines` | Every 10 min, 6 AM–2 AM |
| closing_lines | `https://app.sharppicks.ai/api/cron/closing-lines` | Every 1 min, 10 AM–1 AM |
| grade_picks | `https://app.sharppicks.ai/api/cron/grade-picks` | 3:45 AM, 11:30 AM |
| grade_whatifs | `https://app.sharppicks.ai/api/cron/grade-whatifs` | 4:05 AM, 4:05 PM |
| pretip_validate | `https://app.sharppicks.ai/api/cron/pretip-validate` | 9:55 AM, 4:55 PM |
| backup | `https://app.sharppicks.ai/api/cron/backup` | 3:20 AM daily |
| data_quality | `https://app.sharppicks.ai/api/cron/check-data-quality` | 4:15 AM, 12:15 PM |
| expire_trials | `https://app.sharppicks.ai/api/cron/expire-trials` | Hourly at :10 |
| weekly_summary | `https://app.sharppicks.ai/api/cron/weekly-summary` | Mon 6:30 AM |

## Why 9:00 AM Collect?
Lines typically post 8–10 AM ET. The 9:00 AM collect ensures the 10:15 AM model run has fresh odds. Without it, the 5:05 AM collect may have had partial/no lines.

## Throttling
- run_model, collect_games: 10 min min interval (skip if run again within 10 min)
- Use `?force=true` on run-model to bypass throttle and re-run collect first
