# Sharp Picks - Sports Betting Discipline System

## Overview
Sharp Picks is a sports betting discipline system focused on providing highly selective, statistically advantageous sports betting predictions. The system aims to instill discipline by recommending a maximum of one pick per day, leveraging a machine learning model with a 57.3% test accuracy and a 68.6% walk-forward ATS performance, achieving a +30.9% ROI over 12 seasons. Key features include multi-book odds shopping, real-time spread odds integration, a margin-first prediction algorithm, user management, subscription services, and detailed performance tracking, all presented with a calm, institutional tone.

## Recent Changes (February 16, 2026)
- **Token-based auth (autoscale fix):** Hybrid session + Bearer token auth system replaces Flask session-only auth. Signed JWT-style tokens (itsdangerous, 30-day TTL) stored in localStorage, sent as `Authorization: Bearer` headers. Server checks Flask session first, falls back to Bearer token. Required because Flask sessions don't persist across Replit autoscale instances.
- **All blueprints updated for token auth:** `picks_api.py`, `insights_api.py`, and `admin_api.py` all use `get_current_user_obj()` which supports both session and Bearer token auth. Removed all direct `flask_login.current_user` usage from blueprint files.
- **Frontend token flow:** `useApi.js` exports `setAuthToken()`/`getAuthToken()`, attaches Bearer header to all requests, auto-stores tokens from API responses. `useAuth.jsx` stores token on login/register, clears on logout.
- **Admin dashboard triple auth:** `require_superuser()` checks Flask-Login session → X-Admin-Token → Authorization Bearer header, with session_token validation for Bearer tokens. `/api/admin/token` endpoint also accepts Bearer token to issue admin tokens in autoscale.
- **Admin dashboard auto-token exchange:** Admin HTML page reads Bearer token from localStorage, exchanges it for an admin-specific token via `/api/admin/token` before loading data. `adminFetch()` sends both X-Admin-Token and Bearer headers. All periodic refreshes (dashboard, health checks, cron health) gated behind `ensureAdminToken()` to prevent 401 loops.
- **Dual signup flow:** Landing page and AuthModal now support both "Start Trial" (card-on-file, email verification) and "Create Free Account" (instant access, no card) paths
- **Transparency metrics on landing page:** Replaced volatile win-rate stats with selectivity %, picks/passes count, and deleted count (always 0) — metrics that only improve over time
- **Free tier:** Free accounts skip email verification, get welcome email, land directly in app with limited dashboard (no pick details, no bet tracking, no performance tab)
- **Cron jobs externalized:** All 9 cron endpoints triggered by cron-job.org with `X-Cron-Secret` header authentication
- **Welcome email:** `send_welcome_email()` added for free account signups

## User Preferences
- Focus on spread predictions (not moneylines)
- Prefer high-confidence picks over volume
- Discipline-first approach: one pick per day max
- Calm, institutional tone - no FOMO marketing
- Track all predictions for performance analysis
- Append-only transparency for public record

## System Architecture

### Frontend
The frontend is a React and Vite application with inline CSS, utilizing a dark theme (`#0A0D14`) and specific fonts (IBM Plex Serif, Inter, JetBrains Mono). It features a 4-tab shell (Picks, Insights, Performance, Profile), a marketing landing page, components for displaying picks, performance metrics, user profiles, and subscription management. UI elements include skeleton loading states, empty states, and abstract blurred charts for free-tier users. The Insights tab offers educational content on betting discipline and model methodology.

### Backend
The backend is built with Python/Flask, serving as the API layer, static file server, and handling user authentication, Stripe integrations, scheduled tasks, and ML model interfacing.

### ML Algorithm
The core ML model uses 56 features to predict game outcomes with a margin-first approach, converting expected margins to cover probabilities via Normal CDF. It integrates real-time odds, calculates implied probabilities, and applies market shrinkage and edge caps for disciplined predictions. Data collection scripts gather scores, odds, team ratings, injury data, and schedules. The prediction logic ensures a maximum of one pick per day with an edge threshold of >= 3.5%, incorporating a market-aware shrinkage (MODEL_WEIGHT=0.3).

### Data Architecture
PostgreSQL is used for user data, picks, passes, model runs, bets, referrals, insights, and cron job logs. SQLite stores legacy game data and ML training data. Tables are append-only for transparency. Data collection includes daily line refreshes, quality checks, and game grading, with all date logic standardized to Eastern Time.

### API Endpoints
The API provides endpoints for authentication, pick delivery, public statistics, subscription management, bet tracking, and insights content. It supports user registration, login, password resets, fetching data, Stripe integration, and user-tracked bets. Cron job endpoints are HTTP-triggered via cron-job.org, secured by `X-Cron-Secret` header, and log all executions to `cron_logs` table for health monitoring. An admin dashboard provides superuser-only access to revenue, model stats, user management, health checks, cron job monitoring, and data exports. Admin dashboard uses client-side API auth (not Flask session) for autoscale compatibility.

### Freemium Tier Model
Dual signup flow supports free accounts and trial accounts. Free accounts (subscription_status='free', is_premium=False) can see model activity, public record, and pass-day summaries but cannot see pick details (side, spread, edge %), bet tracking, or performance dashboard. Pro accounts (via 14-day card-on-file trial or paid subscription) get full access. Landing page has dual CTA: "Start 14-Day Trial" (primary) and "Create Free Account" (secondary). AuthModal registration shows both paths with "Start Trial — Card Required" and "Create Free Account" buttons. Free accounts skip email verification and land directly in the app. The free tier reduces trial abuse by giving tire-kickers a home without burning a trial slot.

### Key Design Decisions
The system enforces a "no pick" policy when no sufficient edge is found. Transparency is maintained through append-only tables and clear labeling of calibration changes. User engagement features include a 14-day card-on-file trial and tiered pricing. The system maintains a calm, institutional tone. Anti-abuse measures include email verification, Gmail alias normalization, card-on-file trials, login rate limiting, and trial_used flags. Security hardening involves CORS restrictions, access controls for sensitive APIs, session invalidation, webhook idempotency, and atomic founding member assignment. Notifications (push, email) are used for pick alerts, pass-day alerts, results, and weekly summaries. Daily pg_dump and JSON backups are performed. Cron job monitoring tracks execution status and detects overdue jobs. All date logic uses Eastern Time. Compliance disclaimers are integrated. Multi-book odds shopping, real sportsbook juice integration, and closing line value (CLV) tracking are central. Automated risk filters and fail-safe mechanisms prevent unreliable picks.

## External Dependencies
- **PostgreSQL**: Primary database.
- **SQLite**: Historical game data and ML training data.
- **Stripe**: Payment processing for subscriptions.
- **ESPN**: Game scores data.
- **The-Odds-API**: Real-time sports betting odds from multiple sportsbooks (DraftKings, FanDuel, BetMGM, Caesars, PointsBet, BetRivers).
- **OneSignal**: Push notification delivery.
- **Resend**: Transactional email delivery.
- **Flask-Login**: User session management and authentication.
- **SQLAlchemy**: ORM for database interactions.
- **Gunicorn**: Production HTTP server.
- **cron-job.org**: External cron scheduler for all 9 scheduled endpoints.