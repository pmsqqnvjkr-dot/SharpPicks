# Sharp Picks - Sports Betting Discipline System

## Overview
Sharp Picks is a sports betting discipline system designed to provide highly selective, statistically advantageous sports betting predictions. Its core purpose is to instill betting discipline by recommending a maximum of one pick per day. The system leverages a machine learning model with a proven 57.3% test accuracy and a 68.6% walk-forward ATS performance, yielding a +30.9% ROI over 12 seasons. The project aims to deliver these services with a calm, institutional tone, prioritizing long-term profitability and transparent performance tracking. Key capabilities include multi-book odds shopping, real-time spread odds integration, a margin-first prediction algorithm, comprehensive user management, subscription services, and detailed performance tracking.

## User Preferences
- Focus on spread predictions (not moneylines)
- Prefer high-confidence picks over volume
- Discipline-first approach: one pick per day max
- Calm, institutional tone - no FOMO marketing
- Track all predictions for performance analysis
- Append-only transparency for public record

## System Architecture

### Frontend
The frontend is a React and Vite application with inline CSS, utilizing a dark theme (`#0A0D14`) and specific fonts (IBM Plex Serif, Inter, JetBrains Mono). It features a 4-tab shell (Picks, Insights, Performance, Profile), a marketing landing page, and components for displaying picks, performance metrics, user profiles, and subscription management. UI elements include skeleton loading states, empty states, and abstract blurred charts for free-tier users. The application supports Capacitor for native iOS/Android push notifications, falling back to web FCM.

### Backend
The backend is built with Python/Flask, serving as the API layer, static file server, and handling user authentication (hybrid session + Bearer token auth), Stripe integrations, scheduled tasks, and ML model interfacing. It includes cron jobs for pre-tip re-validation, push notifications, and admin health alerts.

### ML Algorithm (NBA — Live)
The core ML model uses 56 features to predict game outcomes with a margin-first approach, converting expected margins to cover probabilities. It integrates real-time odds, calculates implied probabilities, and applies market shrinkage and edge caps. The prediction logic enforces a maximum of one pick per day with a dynamic edge threshold scaled by spread elasticity (Required Edge = 3.0% + Spread × 0.167, capped at 7.0%), incorporating market-aware shrinkage (MODEL_WEIGHT=0.3). Risk layers include Steam Fragility Score, distinct rest penalties, spread-risk edge weighting, and star injury confirmation gates. An automated kill switch monitors rolling 100-bet ROI, CLV negativity, and edge decay signal to auto-reduce position size by 50% if all three conditions trigger.

### WNBA Model Status — MARGINAL, NOT SHIPPED (Awaiting 2025 Live Validation)
Baseline backtest (basic features, GBR): best 51.0% / -2.7% ROI. Enhanced leak-free backtest (rolling game-by-game ratings + prior-season player impact + regularized XGBoost): best 54.3% / +3.7% ROI over 127 bets, but profitable in only 1/2 test seasons (2023: +10.5u, 2024: -5.7u). Model MAE 10.0 vs Market 8.9. Prior version showed +19.5% ROI but used static end-of-season ratings (data leakage — now fixed). Strategy: collect 2025 live data, re-test after Sept 2025 with 3 test seasons. Ship only if 55%+ WR / positive ROI holds consistently. Files: `wnba_backtest.py`, `wnba_enhanced_backtest.py`, `wnba_data_pipeline.py`, `sport_config.py` (`live: False`).

### Data Architecture
PostgreSQL is used for user data, picks, passes, model runs, bets, referrals, insights, and cron job logs. SQLite stores legacy game data and ML training data. Tables are append-only for transparency. Data collection includes daily line refreshes, quality checks, and game grading, with all date logic standardized to Eastern Time.

### API Endpoints
The API provides endpoints for authentication, pick delivery, public statistics, subscription management, bet tracking, and insights content. It supports user registration, login, password resets, fetching data, Stripe integration, and user-tracked bets. Cron job endpoints are HTTP-triggered externally and secured. An admin dashboard provides superuser-only access to revenue, model stats, user management, health checks, cron job monitoring, and data exports.

### Freemium Tier Model
The system supports dual signup for free and trial accounts. Free accounts have limited access (model activity, public records, pass-day summaries), while Pro accounts (via 14-day card-on-file trial or paid subscription) receive full access, aiming to reduce trial abuse.

### Key Design Decisions
The system enforces a "no pick" policy without sufficient edge. Transparency is maintained through append-only tables and clear labeling of calibration changes. Anti-abuse measures include email verification, Gmail alias normalization, card-on-file trials, and login rate limiting. Security hardening involves CORS restrictions, access controls, session invalidation, and webhook idempotency. Notifications (push, email) are used for pick alerts, pass-day alerts, results, and weekly summaries. Daily database backups are performed. Cron job monitoring tracks execution status. Multi-book odds shopping, real sportsbook juice integration, and closing line value (CLV) tracking are central, alongside automated risk filters and fail-safe mechanisms. Rolling performance and risk-of-ruin metrics are used for internal model governance.

### Critical Architecture Notes
Development and production use separate PostgreSQL databases; cron jobs must target the production URL. The `seed_database()` function handles admin account creation, historical data seeding, and schema migrations. `db.create_all()` does not add new columns to existing tables, requiring explicit `ALTER TABLE` statements in `seed_database()` for schema changes.

## External Dependencies
- **PostgreSQL**: Primary relational database.
- **SQLite**: Legacy game data and ML training data storage.
- **Stripe**: Payment processing for subscriptions.
- **ESPN**: Source for game scores data.
- **The-Odds-API**: Provides real-time sports betting odds from various sportsbooks.
- **Firebase Cloud Messaging (FCM)**: Used for push notification delivery.
- **Resend**: Transactional email delivery service.
- **Flask-Login**: Manages user sessions and authentication.
- **SQLAlchemy**: Object Relational Mapper (ORM) for Python database interactions.
- **Gunicorn**: Production HTTP server for Python web applications.
- **cron-job.org**: External service for scheduling cron jobs.