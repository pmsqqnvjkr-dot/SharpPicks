# Sharp Picks - Sports Betting Discipline System

## Overview
Sharp Picks is a sports betting discipline system. One pick per day maximum, only when the model detects a statistical edge above threshold. Most days, the app says nothing. Silence is the product working.

## Current Status (Feb 2026)
- **Model Accuracy**: 79.4% on test data (15,131 games)
- **Brier Score**: 0.139 (excellent calibration)
- **Features**: 36 features including pace, ratings, line movement
- **Backtest ROI**: +47.26% simulated on historical data
- **Live Record**: 20-30 (prediction_log in SQLite)

## Tech Stack
- **Frontend**: React + Vite (port 5000), Tailwind CSS
- **Backend**: Python/Flask (port 8000)
- **Databases**: 
  - PostgreSQL (via DATABASE_URL) - User accounts, auth
  - SQLite (sharp_picks.db) - Games, predictions, model data
- **Auth**: Email/Password (Flask-Login with session management)
- **Payments**: Stripe integration installed

## New App Concept (from spec doc)
The app is being redesigned as a discipline-first betting system:
- **One pick per day max** - only when edge >= 3.5%
- **"No Pick" days are a feature** - silence means the model is working
- **Append-only transparency** - picks and passes tables never updated/deleted
- **27-screen flow** with 3 tabs: Today, Dashboard, Profile
- **Founding member system** - first 500 paid subscribers get $99/yr rate
- **Pricing**: Free / $29 monthly / $99 annual (founding) / $149 annual (standard)
- **14-day free trial** on all paid plans
- **Design tokens**: Dark theme (#0A0D14 bg), IBM Plex Serif + Inter + JetBrains Mono
- **Tone**: Calm, institutional, no FOMO, no exclamation marks

### New Data Architecture (target)
- `users` - UUID primary key, founding_member, subscription tiers
- `picks` - APPEND-ONLY, one per day max, edge_pct >= 3.5 threshold
- `passes` - APPEND-ONLY, logged when model runs but finds no edge
- `model_runs` - audit trail of every model execution
- `user_bets` - optional user-entered bet tracking
- `referrals` - referral system with 14-day credit
- `founding_counter` - tracks first 500 paid subscribers

### New API Endpoints (target)
- Auth: signup, verify-email, login, forgot/reset-password
- Picks: /picks/today, /picks/history, /picks/:id
- Public: /public/record, /public/stats, /public/founding-count
- Subscriptions: create, cancel, pause, resume, switch
- Webhooks: Stripe payment events

## Current Key Files
### ML Algorithm (KEEP - core prediction engine)
- `model.py` - Ensemble ML prediction model (36 features, 79.4% accuracy)
- `main.py` - Data collection script (ESPN scores, odds API)
- `nba_ratings.py` - Team pace/ratings fetcher (with retry logic)
- `nba_injuries.py` - Injury data fetcher with player impact scoring
- `nba_schedule.py` - Schedule/fatigue analysis (B2Bs, travel, altitude)
- `performance_tracker.py` - Prediction logging/tracking with closing line

### Frontend
- `src/SharpPicksBestOfBoth.jsx` - Main consumer app (redesigned)
- `src/App.jsx` - Router
- `src/components/` - TrustBanner, TodaysPicks, ModelTransparency

### Backend
- `app.py` - Flask API backend (port 8000)
- `models.py` - SQLAlchemy User model with password hashing
- `auth.py` - Email/password authentication blueprint

## Recent Changes
- **Feb 11**: Updated game results for 2/3 and 2/4 via ESPN API
- **Feb 11**: Fixed /api/recent-results to show all resolved wins (was 24hr window)
- **Feb 11**: Made header record display dynamic from API data
- **Feb 4**: Switched to ESPN free injuries API, added CLV stats, sharp money indicators
- Earlier: Converted to React, added email/password auth, PostgreSQL for users

## User Preferences
- Focus on spread predictions (not moneylines)
- Prefer high-confidence picks over volume
- Discipline-first approach: one pick per day max
- Calm, institutional tone - no FOMO marketing
- Track all predictions for performance analysis
- Append-only transparency for public record
