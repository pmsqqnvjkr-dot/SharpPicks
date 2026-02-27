# Sharp Picks - Sports Betting Discipline System

## Overview
Sharp Picks is a sports betting discipline system designed to provide highly selective, statistically advantageous sports betting predictions. Its core purpose is to instill betting discipline by recommending a maximum of one pick per day. The system leverages a machine learning model with a proven 57.3% test accuracy and a 68.6% walk-forward ATS performance, yielding a +30.9% ROI over 12 seasons. Key capabilities include multi-book odds shopping, real-time spread odds integration, a margin-first prediction algorithm, comprehensive user management, subscription services, and detailed performance tracking. The project aims to deliver these services with a calm, institutional tone, prioritizing long-term profitability and transparent performance tracking.

## User Preferences
- Focus on spread predictions (not moneylines)
- Prefer high-confidence picks over volume
- Discipline-first approach: one pick per day max
- Calm, institutional tone - no FOMO marketing
- Track all predictions for performance analysis
- Append-only transparency for public record

## System Architecture

### Frontend
The frontend is a React and Vite application with inline CSS, utilizing a dark theme (`#0A0D14`) and specific fonts (IBM Plex Serif, Inter, JetBrains Mono). It features a 4-tab shell (Picks, Insights, Performance, Profile), a marketing landing page, components for displaying picks, performance metrics, user profiles, and subscription management. UI elements include skeleton loading states, empty states, and abstract blurred charts for free-tier users. The Insights tab offers educational content on betting discipline and model methodology. The application supports Capacitor for native iOS/Android push notifications, falling back to web FCM.

### Backend
The backend is built with Python/Flask, serving as the API layer, static file server, and handling user authentication (hybrid session + Bearer token auth for autoscale compatibility), Stripe integrations, scheduled tasks, and ML model interfacing. It includes cron jobs for pre-tip re-validation, push notifications, and admin health alerts.

### ML Algorithm
The core ML model uses 56 features to predict game outcomes with a margin-first approach, converting expected margins to cover probabilities via Normal CDF. It integrates real-time odds, calculates implied probabilities, and applies market shrinkage and edge caps. The prediction logic enforces a maximum of one pick per day with a dynamic edge threshold scaled by spread elasticity (Required Edge = 3.0% + Spread × 0.167, capped at 7.0%), incorporating market-aware shrinkage (MODEL_WEIGHT=0.3). Key risk layers include: (1) Steam Fragility Score replacing flat line-move penalties — SFS = f(magnitude, spread_size, dispersion) applied as Edge × (1 - SFS) with max 60% fragility cap; (2) distinct rest penalties (All-Star break and generic long rest); (3) spread-risk edge weighting; (4) star injury confirmation gates. Edge decay tracking logs prediction snapshots at open and pre-tip for stability analysis. Regime detection segments performance by favorite/dog, spread bucket, and home/away to detect concentration risk. Automated kill switch monitors three conditions simultaneously: rolling 100-bet ROI < -8%, CLV negative >60% of last 50 picks, and edge decay signal stale — when all three trigger, position size auto-reduces to 50% without manual intervention; recovery requires positive rolling ROI and improving CLV trend.

### Data Architecture
PostgreSQL is used for user data, picks, passes, model runs, bets, referrals, insights, and cron job logs. SQLite stores legacy game data and ML training data. Tables are append-only for transparency. Data collection includes daily line refreshes, quality checks, and game grading, with all date logic standardized to Eastern Time.

### API Endpoints
The API provides endpoints for authentication, pick delivery, public statistics, subscription management, bet tracking, and insights content. It supports user registration, login, password resets, fetching data, Stripe integration, and user-tracked bets. Cron job endpoints are HTTP-triggered externally and secured by an `X-Cron-Secret` header, logging all executions for health monitoring. An admin dashboard provides superuser-only access to revenue, model stats, user management, health checks, cron job monitoring, and data exports, using client-side API auth for autoscale compatibility.

### Freemium Tier Model
The system features a dual signup flow supporting free and trial accounts. Free accounts can view model activity, public records, and pass-day summaries but are restricted from accessing pick details, bet tracking, or the full performance dashboard. Pro accounts, available via a 14-day card-on-file trial or paid subscription, receive full access. This model aims to reduce trial abuse by offering a viable option for users to explore the system without committing to a trial.

### Key Design Decisions
The system enforces a "no pick" policy without sufficient edge. Transparency is maintained through append-only tables and clear labeling of calibration changes. Anti-abuse measures include email verification, Gmail alias normalization, card-on-file trials, and login rate limiting. Security hardening involves CORS restrictions, access controls, session invalidation, and webhook idempotency. Notifications (push, email) are used for pick alerts, pass-day alerts, results, and weekly summaries. Daily pg_dump and JSON backups are performed. Cron job monitoring tracks execution status. Multi-book odds shopping, real sportsbook juice integration, and closing line value (CLV) tracking are central, alongside automated risk filters and fail-safe mechanisms. Rolling performance and risk-of-ruin metrics are used for internal model governance.

## Critical Architecture Notes
- **Development and production use SEPARATE PostgreSQL databases.** Cron jobs on cron-job.org MUST target the production URL (`https://app.sharppicks.ai/api/cron/...`), NOT the dev URL. Otherwise, picks/passes only get created in the dev database and won't appear for production users.
- The `seed_database()` function runs on startup and handles: admin account creation, historical data seeding, schema migrations (e.g., adding missing columns), and live pick insertion for data sync.
- `db.create_all()` does NOT add new columns to existing tables. Any schema changes (new columns) must be handled via explicit `ALTER TABLE` statements in `seed_database()`.

## Recent Changes
- **2026-02-27**: Built `wnba_data_pipeline.py` — comprehensive WNBA data backfill tool with ESPN score scraping, Odds API historical odds backfill, and schedule feature enrichment. Backfilled 667 WNBA games with spread/total/moneyline data across 2022-2024 seasons (2024 at 99% coverage). Data now SUFFICIENT for walk-forward backtesting. Added WNBA cron throttle intervals. Commands: `--backfill-scores`, `--backfill-odds [max_calls] [year]`, `--enrich`, `--report`, `--quota`.
- **2026-02-26**: Added production-to-dev database sync system — `/api/admin/export-picks` exports all picks, passes, and model runs as JSON from production; `/api/admin/sync-from-prod` pulls from production and upserts into dev database. Both secured by admin auth or cron secret. Keeps dev and prod databases in sync.
- **2026-02-26**: Added `/api/admin/manual-grade` endpoint — allows manual grading of specific picks by providing pick_id, home_score, and away_score. Secured by admin auth or cron secret.
- **2026-02-26**: Enhanced `grade_pending_picks()` with ESPN API fallback — when SQLite game data is missing, fetches scores directly from ESPN scoreboard API. Added detailed logging throughout grading process. Sport-aware ESPN URL (NBA vs WNBA).
- **2026-02-26**: Added `?force=1` parameter to `/api/cron/grade-picks` to bypass throttle.
- **2026-02-26**: Fixed markdown rendering in InsightsTab — inline `**bold**` and `*italic*` now properly parsed via `parseInlineMarkdown()`. Multi-line blockquotes (`> **SHARP PRINCIPLE**\n> *quote*`) extract label and body into styled SharpPrincipleBlock. Standalone `*Evan*` signature lines suppressed (FounderSignature component handles this).
- **2026-02-25**: Added Today's Pipeline panel to admin Command Center — shows today's model run status (waiting/pick/pass), games analyzed, edge detected, run duration, pick or pass details with what-if analysis, and cron attempt history. New `/api/admin/today-pipeline` endpoint. Panel sits between Status Banner and Infrastructure & Ops sections, auto-refreshes every 60s.
- **2026-02-21**: Restructured admin Command Center dashboard — added green/yellow/red status banner at top with at-a-glance system health summary and alerts panel. Reordered sections to match operator mental model: Status Banner → Infrastructure & Ops → NBA Performance → WNBA Performance → Revenue & Sales → Users. Made Control Room a collapsible section. New `/api/admin/status-summary` endpoint aggregates cron health, model run status, kill switch state, and external services into single status indicator.
- **2026-02-21**: Added model signal diagnostic — tracks model-only (unblended) cover probability and edge on every pick. New columns `model_only_cover_prob` and `model_only_edge` on Pick model. New `/api/admin/model-signal` endpoint compares blended vs model-only win rate, ROI, and edge-outcome correlation on a consistent sample. After 50+ picks, this will reveal whether MODEL_WEIGHT=0.3 should increase (model adds signal) or stay/decrease (market does the heavy lifting).
- **2026-02-18**: Moved Risk Profile from public Performance tab to admin-only Control Room alongside other model metrics. Control Room now has 7 panels: Risk Profile, Trigger States, Threshold Tuning, Bucket Segmentation, Decay Metrics, Fragility Scoring, Experimental Toggles.
- **2026-02-18**: Moved model metrics (Calibration, Edge Decay, Regime Detection, Kill Switch) from public Performance tab to admin-only Control Room in Command Center. Added `/api/admin/control-room` endpoint.
- **2026-02-18**: Implemented automated kill switch system — KillSwitch model, `/api/public/kill-switch` endpoint, position_size_pct on Pick model. Monitors rolling ROI, CLV trend, and edge decay; auto-reduces position to 50% when all 3 conditions trigger.

## Cron Job Schedule (cron-job.org)
All cron endpoints are POST requests secured with `X-Cron-Secret` header. All times are Eastern Time (ET).

| Job | Endpoint | Schedule (ET) | Purpose |
|---|---|---|---|
| Pre-Tip Validate | `/api/cron/pretip-validate` | 9:55 AM + 4:55 PM | Final sanity checks before pick window |
| SP — Daily Backup | `/api/cron/backup` | Daily 3:20 AM | Backups + retention |
| SP — Data Quality | `/api/cron/check-data-quality` | 4:15 AM + 12:15 PM | Detect missing lines/games/odds gaps |
| SP — Collect Games (AM) | `/api/cron/collect-games` | 5:05 AM | Pull today/next slate early |
| SP — Collect Games (PM) | `/api/cron/collect-games` | 1:05 PM | Catch late adds/time changes |
| SP — Run Model (AM) | `/api/cron/run-model` | 10:15 AM | Run model, generate pick or pass |
| SP — Run Model (PM) | `/api/cron/run-model` | 2:15 PM | Re-run if AM didn't produce result |
| SP — Refresh Lines | `/api/cron/refresh-lines` | Every 10 min, 6 AM–2 AM | Keep current lines fresh |
| SP — Closing Lines 1–4 | `/api/cron/closing-lines` | Every min, 10 AM–1 AM (×4 shards) | High-resolution closing capture |
| SP — Grade Picks | `/api/cron/grade-picks` | 3:45 AM + 11:30 AM | Grade completed events |
| SP — Grade What-Ifs | `/api/cron/grade-whatifs` | 4:05 AM + 4:05 PM | Recalcs / counterfactuals |
| SP — Expire Trials | `/api/cron/expire-trials` | Hourly at :10 | Access control cleanup |
| SP — Weekly Summary | `/api/cron/weekly-summary` | Mon 6:30 AM | Weekly performance reporting |

**Header required for all**: `X-Cron-Secret: <your CRON_SECRET value>`
**Method**: POST (no body required)

## External Dependencies
- **PostgreSQL**: Primary database.
- **SQLite**: Historical game data and ML training data.
- **Stripe**: Payment processing for subscriptions.
- **ESPN**: Game scores data.
- **The-Odds-API**: Real-time sports betting odds from multiple sportsbooks (DraftKings, FanDuel, BetMGM, Caesars, PointsBet, BetRivers).
- **Firebase Cloud Messaging (FCM)**: Push notification delivery.
- **Resend**: Transactional email delivery.
- **Flask-Login**: User session management and authentication.
- **SQLAlchemy**: ORM for database interactions.
- **Gunicorn**: Production HTTP server.
- **cron-job.org**: External cron scheduler.