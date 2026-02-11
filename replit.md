# Sharp Picks - Sports Betting Discipline System

## Overview
Sharp Picks is a sports betting discipline system. One pick per day maximum, only when the model detects a statistical edge above threshold. Most days, the app says nothing. Silence is the product working.

## Current Status (Feb 2026)
- **Model Accuracy**: 79.4% on test data (15,131 games)
- **Brier Score**: 0.139 (excellent calibration)
- **Features**: 36 features including pace, ratings, line movement
- **Backtest ROI**: +47.26% simulated on historical data
- **Live Record**: 6-1 (7 picks, 23 passes, 85.7% win rate, +436u)

## Tech Stack
- **Frontend**: React + Vite (port 5000 dev), inline CSS with design tokens
- **Backend**: Python/Flask (port 8000 dev, port 5000 production via gunicorn)
- **Databases**: 
  - PostgreSQL (via DATABASE_URL) - Users, picks, passes, model runs, bets, referrals
  - SQLite (sharp_picks.db) - Legacy games/predictions, ML model training data
- **Auth**: Email/Password (Flask-Login with session management, password reset via tokens)
- **Payments**: Stripe integration (via Replit connector)
- **Design**: Dark theme (#0A0D14), IBM Plex Serif + Inter + JetBrains Mono
- **Deployment**: Autoscale via gunicorn, Vite build → Flask serves static files

## App Architecture

### Frontend (React + Vite)
- `src/App.jsx` - Router entry point (main app + password reset route)
- `src/pages/SharpPicksApp.jsx` - Main 3-tab shell with landing page for new visitors
- `src/pages/ResetPassword.jsx` - Password reset page (token-based)
- `src/hooks/useApi.js` - API fetch hooks
- `src/hooks/useAuth.jsx` - Auth context provider
- `src/index.css` - Design tokens (CSS variables, fonts)

### Components (`src/components/sharp/`)
- `LandingPage.jsx` - Marketing landing page for non-authenticated visitors
- `TabNav.jsx` - Bottom tab navigation (Today, Dashboard, Profile)
- `TodayTab.jsx` - Today's pick/pass/waiting state display
- `PickCard.jsx` - Pick detail card (locked for free users)
- `NoPickCard.jsx` - "Discipline preserved" pass day card
- `DashboardTab.jsx` - Performance stats, equity curve, streaks, monthly breakdown
- `ProfileTab.jsx` - User profile, settings menu, pricing plans
- `AuthModal.jsx` - Login/register/forgot-password modal
- `PickHistoryScreen.jsx` - Full pick history with filtering
- `HowItWorksScreen.jsx` - Model methodology and stats
- `BetTrackingScreen.jsx` - User bet tracking
- `ReferralScreen.jsx` - Referral code and link sharing
- `NotificationsScreen.jsx` - Notification preferences

### Backend (Flask)
- `app.py` - Main Flask app with auth, Stripe, scheduled tasks, SPA serving
- `models.py` - SQLAlchemy models (User, Pick, Pass, ModelRun, UserBet, Referral, FoundingCounter, TrackedBet)
- `picks_api.py` - /api/picks/* endpoints (today, history, detail)
- `public_api.py` - /api/public/* endpoints (record, stats, founding-count)
- `model_service.py` - Bridges ML model to picks/passes tables
- `stripe_client.py` - Stripe API client via Replit connector

### ML Algorithm (core prediction engine)
- `model.py` - Ensemble ML prediction model (36 features, 79.4% accuracy)
- `main.py` - Data collection script (ESPN scores, odds API)
- `nba_ratings.py` - Team pace/ratings fetcher
- `nba_injuries.py` - Injury data with player impact scoring
- `nba_schedule.py` - Schedule/fatigue analysis
- `performance_tracker.py` - Prediction logging with closing line

### Data Architecture (PostgreSQL)
- `users` - UUID PK, founding_member, subscription tiers, referral codes
- `picks` - APPEND-ONLY, one per day max, edge_pct >= 3.5 threshold
- `passes` - APPEND-ONLY, logged when model finds no qualifying edge
- `model_runs` - Audit trail of every model execution
- `user_bets` / `tracked_bets` - User-entered bet tracking
- `referrals` - Referral system with 14-day credit
- `founding_counter` - Tracks first 500 paid subscribers

### API Endpoints
- Auth: /api/auth/register, /api/auth/login, /api/auth/logout, /api/auth/user
- Auth: /api/auth/forgot-password, /api/auth/reset-password
- Picks: /api/picks/today, /api/picks/history, /api/picks/:id
- Public: /api/public/record, /api/public/stats, /api/public/founding-count
- Subscriptions: /api/subscriptions/create-checkout, /api/subscriptions/cancel, /api/subscriptions/status
- Bets: /api/bets (GET/POST), /api/bets/:id/result, /api/bets/:id (DELETE)
- Stripe: /api/stripe/config, /api/stripe/webhook, /api/stripe/products
- User: /api/user/stats

## Key Design Decisions
- One pick per day max, edge threshold >= 3.5%
- "No Pick" days are a feature - silence means the model is working
- Append-only picks/passes tables for complete transparency
- 14-day free trial on all paid plans
- Founding member system: first 500 paid subscribers get $99/yr rate
- Pricing: Free / $29 monthly / $99 annual (founding) / $149 annual (standard)
- Calm, institutional tone - no FOMO, no exclamation marks
- Landing page for new visitors, app shell for returning users
- Password reset via secure time-limited tokens (1 hour expiry)
- Webhook signature verification required in production

## Recent Changes
- **Feb 11**: Fixed data integrity - deduplicated picks to 1/day, backfilled 23 pass records
- **Feb 11**: Improved Dashboard with streak tracking, monthly breakdown, gradient equity curve
- **Feb 11**: Built landing page with live stats, value props, and founding member CTA
- **Feb 11**: Added password reset flow (forgot password + token-based reset page)
- **Feb 11**: Production deployment config (gunicorn, Vite build, SPA serving)
- **Feb 11**: Fixed webhook to properly track trial status and enforce signature in production
- **Feb 11**: Complete frontend redesign with new design system (dark theme, 3 fonts)
- **Feb 11**: Built 3-tab layout: Today, Dashboard, Profile
- **Feb 11**: Added Pick History, How It Works, Bet Tracking, Referral, Notifications screens
- **Feb 11**: Stripe subscription checkout with founding member logic

## User Preferences
- Focus on spread predictions (not moneylines)
- Prefer high-confidence picks over volume
- Discipline-first approach: one pick per day max
- Calm, institutional tone - no FOMO marketing
- Track all predictions for performance analysis
- Append-only transparency for public record
