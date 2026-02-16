# Sharp Picks - Sports Betting Discipline System

## Overview
Sharp Picks is a sports betting discipline system designed to provide highly selective sports betting predictions. Its core purpose is to identify a maximum of one statistically advantageous pick per day, operating under the principle that "silence is the product working." The system aims to instill discipline in sports betting by only recommending bets when a significant statistical edge is detected by its advanced model.

The project boasts a robust machine learning model with a 57.3% test accuracy and a 68.6% walk-forward ATS performance. It has achieved a +30.9% ROI over 12 seasons. Key capabilities include multi-book odds shopping, real-time spread odds integration, and a sophisticated margin-first prediction algorithm. The system also features comprehensive user management, subscription services, and detailed performance tracking, all presented with a calm, institutional tone to foster a discipline-first betting approach.

## User Preferences
- Focus on spread predictions (not moneylines)
- Prefer high-confidence picks over volume
- Discipline-first approach: one pick per day max
- Calm, institutional tone - no FOMO marketing
- Track all predictions for performance analysis
- Append-only transparency for public record

## System Architecture

### Frontend
The frontend is built with React and Vite, utilizing inline CSS with design tokens for a consistent dark theme (`#0A0D14`) using IBM Plex Serif, Inter, and JetBrains Mono fonts. The application features a 4-tab shell (Picks, Insights, Performance, Profile), a marketing landing page for non-authenticated users, and a comprehensive suite of components for displaying picks, performance metrics, user profiles, and subscription management. Key features include skeleton loading states, designed empty states, and abstract blurred charts for free-tier users. The Insights tab provides educational content on betting discipline, market dynamics, and model methodology with category filters and a pass-day CTA integration.

### Backend
The backend is developed with Python/Flask, serving as the API layer and static file server for the React frontend. It manages user authentication, Stripe integrations, scheduled tasks, and acts as the bridge between the ML model and the database.

### ML Algorithm
The core of Sharp Picks is an ensemble ML prediction model. It uses 56 features, including pace, ratings, and line movement, to predict game outcomes. The algorithm employs a margin-first prediction approach, converting expected margins to cover probabilities via Normal CDF. It integrates real-time odds from multiple sportsbooks, calculates implied probabilities, and applies a market shrinkage factor and edge caps to ensure realistic and disciplined predictions. Data collection scripts fetch scores, odds, team ratings, injury data, and schedules.

### Data Architecture
The system primarily uses PostgreSQL for user data, picks, passes, model runs, bets, referrals, and insights. SQLite is used for legacy game data and ML model training data. Key tables are designed for append-only operations to maintain complete transparency and auditability of picks and passes. Data is meticulously collected, with daily jobs for refreshing lines, quality checks, and game grading. All date logic uses Eastern Time (America/New_York) to align with NBA schedules.

### API Endpoints
The API is structured around authentication, pick delivery, public statistics, subscription management, bet tracking, and insights content management. Endpoints handle user registration, login, password resets, fetching daily picks and historical data, managing subscriptions with Stripe, and allowing users to track their bets against published picks.

### Cron Endpoints (added Feb 16, 2026)
HTTP-triggered scheduled job endpoints secured by `X-Cron-Secret` header (CRON_SECRET env var). For use with external cron services (cron-job.org, Render cron, etc.) as a reliable alternative to in-process APScheduler. All endpoints are POST requests returning `{'status': 'done', 'job': '...'}`.
- `/api/cron/collect-games` — Fetch today's NBA games from ESPN
- `/api/cron/refresh-lines` — Refresh odds from all sportsbooks
- `/api/cron/closing-lines` — Capture closing lines before games start
- `/api/cron/grade-picks` — Grade pending picks with final scores
- `/api/cron/grade-whatifs` — Grade what-if passes with final scores
- `/api/cron/expire-trials` — Expire overdue trials + send 2-day warnings
- `/api/cron/weekly-summary` — Generate and send weekly summary email
- `/api/cron/backup` — JSON backup of critical tables + pg_dump
- `/api/cron/check-data-quality` — Validate data freshness and integrity
APScheduler remains active as a fallback for development; in production, use external cron triggers.

### Key Design Decisions
- **Prediction Logic**: One pick per day maximum with an edge threshold of >= 3.5%. "No Pick" days are a fundamental feature, indicating the model found no sufficient edge.
- **Market-Aware Shrinkage**: MODEL_WEIGHT=0.3 blends 30% model prediction with 70% market spread before computing cover probabilities. Validated by out-of-sample testing: Model MAE=12.03 pts vs Market MAE=10.06 pts (market is more accurate 60% of the time). MAX_EDGE_PCT=8.0 caps displayed edges. Calibrated Feb 12, 2026; prior picks used raw predictions without shrinkage and are tagged "Pre-Cal" in the public record.
- **Transparency**: Append-only tables for picks and passes ensure an auditable and transparent record. Calibration changes are noted in the public record API and UI.
- **User Engagement**: Features include a 14-day free trial, a "Founding Member" system for early adopters, and tiered pricing.
- **Tone & UI**: Calm, institutional tone with no FOMO marketing. The UI provides detailed performance dashboards, coaching on win/loss resolutions, and comprehensive bet tracking.
- **Anti-Abuse Protection** (added Feb 16, 2026):
  - Email verification required before trial access (24h expiration, signed tokens)
  - Gmail alias normalization prevents duplicate trials (removes dots, strips +suffixes for gmail.com/googlemail.com)
  - Card-on-file trial: Stripe checkout with trial_period_days=14 ($0 charged, card collected upfront)
  - Login rate limiting: 5 failed attempts → 15 minute lockout
  - trial_used flag prevents repeat free trials per normalized email
  - Lifecycle emails: verification, trial expiring (2-day warning), trial expired, cancellation, payment failed
  - Scheduled jobs: check_expiring_trials (9 AM ET), expire_trials (12:15 AM ET)
  - Performance API shows only published picks record (not all model predictions)
- **Security Hardening** (updated Feb 16, 2026):
  - CORS restricted to sharppicks.ai domains only (+ dev domains in development)
  - API endpoints /api/predictions, /api/recent-results, /api/model/calibration require @login_required + is_pro
  - /api/performance stays public (aggregate published picks record only)
  - Session invalidation on password reset via session_token (stored per-user, validated on every request)
  - Webhook idempotency: ProcessedEvent table with insert-first pattern prevents duplicate Stripe event processing
  - Atomic founding member assignment with PostgreSQL FOR UPDATE row-level lock
  - Subscription reactivation endpoint: /api/subscriptions/reactivate for cancel_at_period_end users
  - 'cancelling' status grants access until current_period_end expires
  - Secure, time-limited tokens for password resets and email verification, webhook signature verification for production
- **Notifications & Engagement** (added Feb 16, 2026):
  - Push notifications via OneSignal REST API (requires ONESIGNAL_APP_ID + ONESIGNAL_API_KEY)
  - Pick alerts: sent to "Pro Users" segment when a qualified pick is published
  - Pass-day alerts: sent to "Pass Alerts" segment on all pass outcomes (no-games, paper-trade, below-threshold)
  - Result notifications: sent on win/loss/push resolution
  - Weekly summary email: Monday 9 AM ET via Resend to all pro users with weekly_summary pref enabled
  - Pass-day onboarding: dedicated step in OnboardingFlow showing "Most days look like this" with mini no-pick preview
- **Database Backups** (added Feb 16, 2026):
  - Daily pg_dump at 3 AM ET to /tmp/backups/ (keeps last 7 days)
  - NOTE: /tmp is ephemeral on Replit deploys; for production, configure external storage (S3/GCS) or rely on Replit's built-in PostgreSQL snapshots
- **Time Zones**: All date logic is standardized to Eastern Time (America/New_York). APScheduler timezone set to America/New_York.
- **Compliance**: Compliance disclaimers are integrated into the UI and API responses.
- **Odds Integration**: Multi-book odds shopping, real sportsbook juice integration, and closing line value (CLV) tracking are central to the prediction and analysis. Single API call to The-Odds-API with all 6 books in one request (not sequential calls per book).
- **Risk Management**: Automated risk filters exclude games with high spreads or missing data, and a fail-safe mechanism prevents picks from being published under uncertain conditions (e.g., stale data, imminent tip-off without injury data).

## External Dependencies
- **PostgreSQL**: Primary database for application data (users, picks, passes, subscriptions, bets, referrals).
- **SQLite**: Used for historical game data and ML model training datasets.
- **Stripe**: Payment processing for subscriptions, integrated via Replit connector.
- **ESPN**: Data source for game scores.
- **The-Odds-API**: Provides real-time sports betting odds (current, opening, closing lines) from multiple sportsbooks (DraftKings, FanDuel, BetMGM, Caesars, PointsBet, BetRivers).
- **OneSignal**: Push notification delivery (optional; requires ONESIGNAL_APP_ID + ONESIGNAL_API_KEY).
- **Resend**: Transactional email delivery (lifecycle emails, weekly summaries).
- **Flask-Login**: For user session management and authentication.
- **SQLAlchemy**: ORM for database interactions.
- **Gunicorn**: Production HTTP server for Flask application.