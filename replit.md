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
The core ML model uses 56 features to predict game outcomes with a margin-first approach, converting expected margins to cover probabilities via Normal CDF. It integrates real-time odds, calculates implied probabilities, and applies market shrinkage and edge caps. The prediction logic enforces a maximum of one pick per day with an edge threshold of >= 3.5%, incorporating a market-aware shrinkage (MODEL_WEIGHT=0.3). Recent enhancements include distinct rest penalties (All-Star break and generic long rest), smooth spread-risk edge weighting, star injury confirmation gates, and line movement decomposition (sharp vs. public steam).

### Data Architecture
PostgreSQL is used for user data, picks, passes, model runs, bets, referrals, insights, and cron job logs. SQLite stores legacy game data and ML training data. Tables are append-only for transparency. Data collection includes daily line refreshes, quality checks, and game grading, with all date logic standardized to Eastern Time.

### API Endpoints
The API provides endpoints for authentication, pick delivery, public statistics, subscription management, bet tracking, and insights content. It supports user registration, login, password resets, fetching data, Stripe integration, and user-tracked bets. Cron job endpoints are HTTP-triggered externally and secured by an `X-Cron-Secret` header, logging all executions for health monitoring. An admin dashboard provides superuser-only access to revenue, model stats, user management, health checks, cron job monitoring, and data exports, using client-side API auth for autoscale compatibility.

### Freemium Tier Model
The system features a dual signup flow supporting free and trial accounts. Free accounts can view model activity, public records, and pass-day summaries but are restricted from accessing pick details, bet tracking, or the full performance dashboard. Pro accounts, available via a 14-day card-on-file trial or paid subscription, receive full access. This model aims to reduce trial abuse by offering a viable option for users to explore the system without committing to a trial.

### Key Design Decisions
The system enforces a "no pick" policy without sufficient edge. Transparency is maintained through append-only tables and clear labeling of calibration changes. Anti-abuse measures include email verification, Gmail alias normalization, card-on-file trials, and login rate limiting. Security hardening involves CORS restrictions, access controls, session invalidation, and webhook idempotency. Notifications (push, email) are used for pick alerts, pass-day alerts, results, and weekly summaries. Daily pg_dump and JSON backups are performed. Cron job monitoring tracks execution status. Multi-book odds shopping, real sportsbook juice integration, and closing line value (CLV) tracking are central, alongside automated risk filters and fail-safe mechanisms. Rolling performance and risk-of-ruin metrics are used for internal model governance.

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