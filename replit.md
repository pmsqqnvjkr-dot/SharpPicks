# Sharp Picks - Sports Betting Discipline System

## Overview
Sharp Picks is a sports betting discipline system. One pick per day maximum, only when the model detects a statistical edge above threshold. Most days, the app says nothing. Silence is the product working.

## Current Status (Feb 2026)
- **Model Accuracy**: 57.3% test, 59.1% walk-forward ATS (15,145 games)
- **Brier Score**: 0.239
- **Features**: 56 features including pace, ratings, line movement
- **Walk-Forward ROI**: +12.8% over 12 seasons (7,576 filtered bets, 4,478-3,098 record)
- **Sigma**: 11.7 pts (margin prediction uncertainty)
- **MAE**: 9.1 pts (margin prediction error)
- **Live Record**: 6-1 (7 picks, 23 passes, 85.7% win rate, +436u)
- **Audit Fields**: sigma, z_score, raw_edge, closing_spread, clv tracked per pick

## Data Leakage Fix (Feb 12)
Historical spread data (2006-2018) had inverted sign convention. The data source used positive spread = home favorite (opposite of US standard where negative = favorite). This caused:
- 64% home cover rate (should be ~50%)
- Positive margin-spread correlation (+0.46, should be negative)
- Inflated backtest: 80%+ ATS, 55% ROI (fake)
**Fix applied**: Negated spread_home, spread_away for all pre-2025 games; recalculated spread_result and line_movement. Post-fix: 48.9% home cover rate, -0.46 correlation, 59.1% ATS / 12.8% ROI walk-forward (realistic).
**Note**: team_ratings table has 0 rows, bdl_* data exists only for current games (17 records). home_record progresses game-by-game (verified: pre-game snapshots, not end-of-season).

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
- `src/pages/SharpPicksApp.jsx` - Main 3-tab shell (Today, Dashboard, Profile) with landing page for new visitors
- `src/pages/ResetPassword.jsx` - Password reset page (token-based)
- `src/hooks/useApi.js` - API fetch hooks
- `src/hooks/useAuth.jsx` - Auth context provider
- `src/index.css` - Design tokens (CSS variables, fonts)

### Components (`src/components/sharp/`)
- `LandingPage.jsx` - Marketing landing page for non-authenticated visitors
- `TabNav.jsx` - Bottom tab navigation (Today, Dashboard, Profile)
- `TodayTab.jsx` - Today's pick/pass/waiting state display (with skeleton loading, inline errors)
- `PickCard.jsx` - Pick detail card (locked for free users)
- `NoPickCard.jsx` - "Discipline preserved" pass day card
- `UnifiedDashboard.jsx` - Main dashboard: performance, equity curve, expected edge, behavioral metrics, selectivity spectrum
- `DashboardTab.jsx` - Legacy model performance stats (accessible via Profile > Pick History)
- `ProfileTab.jsx` - User profile, settings menu, pricing, routes to all sub-screens
- `AuthModal.jsx` - Login/register/forgot-password modal
- `PickHistoryScreen.jsx` - Full pick history with filtering, tap-to-view resolution
- `HowItWorksScreen.jsx` - Model methodology and stats
- `BetTrackingScreen.jsx` - Pick-linked bet tracking with dashboard (equity curve, streaks, monthly breakdown)
- `ReferralScreen.jsx` - Referral code and link sharing
- `NotificationsScreen.jsx` - Notification preferences
- `LoadingState.jsx` - Skeleton loading with shimmer animation ("Checking today's model output...")
- `EmptyState.jsx` - Designed empty states (no picks, no tracked bets, no chart data)
- `FreeTierDashboard.jsx` - Abstract blurred charts, discipline messaging, no quantified metrics
- `UpgradeScreen.jsx` - Full upgrade page with pricing cards, what changes/doesn't change
- `CancelScreen.jsx` - Respectful cancellation flow with reason selection
- `OnboardingFlow.jsx` - 4-step onboarding (one pick max, silence, tracking, founder's note)
- `ResolutionScreen.jsx` - Post-win/loss coaching with process review and discipline reminders
- `WeeklySummary.jsx` - Weekly performance recap with daily log
- `AnnualConversion.jsx` - Monthly to annual upgrade with savings math
- `ErrorStates.jsx` - System status notices (data delay, model recalculation, line moved)

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
- All date logic uses Eastern Time (America/New_York) since NBA schedule runs on ET
- Game dates in SQLite are UTC-based; picks/passes use ET date for consistency
- Score collection tries both ESPN date and next day to handle UTC/ET mismatch
- Model only predicts games that haven't tipped off yet (game_time > now)

## Recent Changes
- **Feb 12**: Real spread odds: model now uses actual sportsbook juice (-102, -115, etc.) instead of hardcoded -110
- **Feb 12**: Spread odds collected from the-odds-api for current, opening, and closing lines (6 new DB columns)
- **Feb 12**: Edge calculations use per-game implied probability from real odds for more accurate EV
- **Feb 12**: Full algorithm rewrite per end-to-end NBA spread spec
- **Feb 12**: Margin-first prediction: GBR predicts expected margin, converts to cover prob via Normal CDF (σ=residual std)
- **Feb 12**: Line move penalty reduced to 1.0%/pt (from 1.5%); hard stop at 2.5+ pts unless edge >= 10%
- **Feb 12**: No picks published when fallback sigma is used (model calibration safety gate)
- **Feb 12**: Unified decision logic: model.py is single source of truth, model_service.py only reads outputs and stores to DB
- **Feb 12**: Production calibration tracking: /api/public/calibration endpoint buckets picks by confidence tier (55-57%, 57-60%, 60%+) and reports actual cover rates vs expected
- **Feb 12**: Pro Dashboard rewrite: 6-section layout (Performance Core, Model Integrity calibration bars, Risk Profile, Discipline Score, Recent Pick Log, Model Health badge)
- **Feb 12**: New /api/public/dashboard-stats endpoint: max drawdown, avg days between picks, avg line movement, avg edge, discipline grade, model health, equity curve, recent picks
- **Feb 12**: Risk filters: spread >11 auto-excluded unless edge ≥8%, missing spread = hard pass
- **Feb 12**: Fail-safe: no pick published if spread/prediction missing, stale data >12h, or <30min to tip without injury data
- **Feb 12**: Pick schema upgraded: predicted_margin, cover_prob, implied_prob, market_odds, sportsbook, line_open, line_close, start_time, result_ats, profit_units
- **Feb 12**: prediction_log upgraded with predicted_margin, implied_prob, edge_vs_market, EV, explanation audit fields
- **Feb 12**: Exactly 3 structured reasoning bullets per pick: rest, net rating, pace/matchup, line value
- **Feb 12**: PickCard shows predicted margin, cover probability, spread, and odds
- **Feb 12**: Proper EV calculation: edge = model_prob - implied_prob (not confidence - 0.5)
- **Feb 12**: Closing line collection: 6:30pm daily job refreshes lines, snapshots as closing, calculates CLV
- **Feb 12**: Data quality checks: 10am daily job detects stale lines, duplicates, missing spreads
- **Feb 12**: Walk-forward validation: season-by-season backtesting with no future leakage
- **Feb 12**: Bankroll guidance: flat staking (1-2u by edge tier) + quarter-Kelly calculation
- **Feb 12**: Compliance disclaimers in picks API and PickCard UI
- **Feb 12**: Fixed CLV beat_close logic to compare spread-at-pick vs closing (not opening vs closing)
- **Feb 12**: Scheduled jobs: 9am/9pm collection, 6:30pm closing lines, 10am data quality, 11:30pm grading
- **Feb 12**: Implemented 10 new screens from 27-screen design spec (Phase 1-3 complete)
- **Feb 12**: Loading State (Screen 23) - Skeleton shimmer loading with calm messaging
- **Feb 12**: Empty States (Screen 11) - Designed empty states for no picks, no bets, no chart data
- **Feb 12**: Free Tier Dashboard (Screen 8) - Abstract blurred charts, discipline messaging, no quantified metrics
- **Feb 12**: Upgrade to Pro (Screen 9) - Full upgrade page with what changes/doesn't change
- **Feb 12**: Cancel Subscription (Screen 10) - Respectful exit with reason selection
- **Feb 12**: Onboarding v2 (Screen 21) - 4-step flow (one pick max, silence, tracking, founder's note)
- **Feb 12**: Win/Loss Resolution (Screens 19/22) - Post-outcome coaching with process review
- **Feb 12**: Weekly Summary (Screen 20) - Weekly performance recap with daily log
- **Feb 12**: Monthly to Annual Conversion (Screen 27) - Savings math for monthly subscribers
- **Feb 12**: Error States (Screen 12) - Data delay, model recalculation notices
- **Feb 12**: Pick History now links to resolution screens for resolved picks
- **Feb 12**: Dashboard shows Free Tier view for non-Pro users
- **Feb 12**: Bet tracking now tied to picks - users select from published picks instead of free-form entry
- **Feb 12**: TrackedBet model linked to picks via pick_id, auto-grades when picks are graded
- **Feb 12**: New /api/bets/trackable endpoint returns recent picks available for tracking
- **Feb 12**: "Track outcome" on PickCard passes pick data directly to bet tracking modal
- **Feb 12**: Fixed founding counter to reflect actual founding members (was showing 500 instead of 499)
- **Feb 11**: Built personalized bet tracking dashboard with equity curve, streaks, monthly breakdown, and detailed stats
- **Feb 11**: Enhanced bet tracking with add-bet form, result marking (W/L), deletion, and personal P&L stats
- **Feb 11**: Auto-grading system: scheduled job checks game results and grades pending picks at 11:30 PM
- **Feb 11**: Pro gating on pick history: free users see teams/dates/results but side/edge are locked
- **Feb 11**: Notification preferences now persist to backend (saved to user.notification_prefs)
- **Feb 11**: Fixed SPA catch-all route conflict (removed duplicate root route)
- **Feb 11**: Fixed data integrity - deduplicated picks to 1/day, backfilled 23 pass records
- **Feb 11**: Improved Dashboard with streak tracking, monthly breakdown, gradient equity curve
- **Feb 11**: Built landing page with live stats, value props, and founding member CTA
- **Feb 11**: Added password reset flow (forgot password + token-based reset page)
- **Feb 11**: Production deployment config (gunicorn, Vite build, SPA serving)
- **Feb 11**: Complete frontend redesign with new design system (dark theme, 3 fonts)
- **Feb 11**: Built 3-tab layout: Today, Dashboard, Profile
- **Feb 11**: Stripe subscription checkout with founding member logic

## User Preferences
- Focus on spread predictions (not moneylines)
- Prefer high-confidence picks over volume
- Discipline-first approach: one pick per day max
- Calm, institutional tone - no FOMO marketing
- Track all predictions for performance analysis
- Append-only transparency for public record
