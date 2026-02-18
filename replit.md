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

## Recent Changes
- **2026-02-18**: Implemented automated kill switch system — KillSwitch model, `/api/public/kill-switch` endpoint, position_size_pct on Pick model, KillSwitchPanel UI component in Performance tab. Monitors rolling ROI, CLV trend, and edge decay; auto-reduces position to 50% when all 3 conditions trigger.

## Cron Job Schedule (cron-job.org)
All cron endpoints are POST requests secured with `X-Cron-Secret` header. All times are Eastern Time (ET).

| Endpoint | Schedule (ET) | Purpose |
|---|---|---|
| `/api/cron/collect-games` | Daily 9:00 AM | Fetch today's NBA games and opening lines from The-Odds-API |
| `/api/cron/refresh-lines` | Every 2 hours (10 AM - 6 PM) | Refresh current spread odds across sportsbooks |
| `/api/cron/pretip-validate` | Daily 5:30 PM | Re-validate today's pick with latest lines before tip-off; may revoke if edge lost |
| `/api/cron/closing-lines` | Daily 7:15 PM | Capture closing lines for CLV tracking |
| `/api/cron/grade-picks` | Daily 11:30 PM | Grade completed picks with final scores from ESPN |
| `/api/cron/grade-whatifs` | Daily 11:45 PM | Grade "what-if" pass scenarios for model transparency |
| `/api/cron/check-data-quality` | Daily 11:50 PM | Validate data integrity and flag anomalies |
| `/api/cron/expire-trials` | Daily 3:00 AM | Check expiring trials, send warnings, expire overdue trials |
| `/api/cron/weekly-summary` | Sundays 10:00 AM | Send weekly performance summary emails to subscribers |
| `/api/cron/backup` | Daily 4:00 AM | pg_dump + JSON backup of picks, passes, users |

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