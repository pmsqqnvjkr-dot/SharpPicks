# NBA Sharp Picks - Betting Analysis System

## Overview
Comprehensive NBA betting analysis system with automated data collection, calibrated ensemble ML models for spread predictions, arbitrage detection, live game analysis, and responsible gambling monitoring.

## Tech Stack
- **Frontend**: React + Vite (port 5000)
- **Backend**: Python/Flask (port 8000)
- **Database**: PostgreSQL (via DATABASE_URL)
- **Auth**: Email/Password (Flask-Login with session management)

## Current Status
- **Model Accuracy**: 79.4% on test data (15,131 games)
- **Brier Score**: 0.139 (excellent calibration)
- **Features**: 36 features including pace, ratings, line movement
- **Backtest ROI**: +47.26% simulated on historical data

## Recent Changes (Feb 2026)
- **Elite Model Improvements** (Feb 4):
  - Fixed injuries API with BALLDONTLIE_API_KEY for real-time player injury data
  - Added Closing Line Value (CLV) stats display showing beat-the-close rate (pro benchmark)
  - Added Sharp Money indicator on picks showing if line moved toward/away from pick
  - Added opening vs current spread display for market awareness
- **Added Elite Model Features** (per betting best practices):
  - Schedule/fatigue factors: B2Bs, rest days, travel distance, altitude effects
  - Coin-flip spread filtering: Option to hide -1.5 to +1.5 spreads (low-edge games)
  - Closing line tracking: Track if picks beat the closing line (pro benchmark)
  - Injury impact scoring: Player-weighted injury reports with status
- **Fixed /api/predictions** - Now calculates all 36 features properly (was only using 11)
- **Added Free Trial System** - 7-day trial via email (no credit card required)
  - POST /api/auth/trial - Start trial with email
  - GET /api/auth/check-trial - Check trial status
  - Security: Email validation, UUID validation, trial expiration enforcement
- **Updated Footer** - Removed donations line, added Terms/Privacy/Support links
- **User Model** - Added trial_ends and trial_used fields
- **Replaced OAuth with Email/Password auth** using Flask-Login
- Added login/registration modal UI in frontend
- Migrated database from SQLite to PostgreSQL
- Added User model with password hashing (Werkzeug)
- Auth-protected API endpoints for bets, upgrade, unit size
- Premium upgrade and unit size now persist to database
- **Converted frontend to React** with Vite build system
- Added TrustBanner component showing model stats
- Added NBA pace/offensive/defensive ratings features
- Implemented sample weighting (recent games weighted higher)
- Added betting filters with minimum confidence threshold
- Created live performance tracking system
- Model now uses 36 features (up from 23)
- Added retry logic with exponential backoff for NBA stats API

## Key Files
- `src/` - React frontend (Vite + React Router)
  - `App.jsx` - Router with 3 routes (/, /app, /analytics)
  - `SharpPicksApp.jsx` - Consumer picks app
  - `AnalyticsDashboard.jsx` - Analytics deep dive
  - `components/TrustBanner.jsx` - Model stats banner
  - `components/TodaysPicks.jsx` - Pick cards with confidence filters
  - `components/ModelTransparency.jsx` - Calibration and performance tracking
- `app.py` - Flask API backend (port 8000)
- `models.py` - SQLAlchemy User model with password hashing
- `auth.py` - Email/password authentication blueprint
- `model.py` - Ensemble ML prediction model
- `main.py` - Data collection script
- `nba_ratings.py` - Team pace/ratings fetcher (with retry logic)
- `nba_injuries.py` - Injury data fetcher with player impact scoring
- `nba_schedule.py` - Schedule/fatigue analysis (B2Bs, travel, altitude)
- `performance_tracker.py` - Prediction logging/tracking with closing line
- `rundown_api.py` - The Rundown API integration
- `arbitrage.py` - Arbitrage opportunity detector

## API Endpoints
- `GET /` - Web dashboard
- `GET /api/predictions` - Today's model predictions with confidence
- `GET /api/performance` - Live performance tracking stats
- `GET /api/model/calibration` - Calibration check by confidence bucket
- `GET /api/admin/stats` - Dashboard stats (games, spreads, etc.)
- `POST /api/auth/register` - Register new user with email/password
- `POST /api/auth/login` - Login with email/password
- `POST /api/auth/logout` - Logout current user
- `GET /api/auth/user` - Current authenticated user info
- `POST /api/auth/upgrade` - Upgrade user to premium (auth required)
- `POST /api/auth/unit-size` - Set user's betting unit size (auth required)
- `POST /api/auth/trial` - Start 7-day free trial with email
- `GET /api/auth/check-trial` - Check trial status (requires user_id)
- `GET/POST /api/bets` - User's tracked bets (auth required)

## Configuration
- Minimum confidence threshold: 55%
- Strong pick threshold: 60%
- Current season games weighted 1.5x higher

## User Preferences
- Focus on spread predictions (not moneylines)
- Prefer high-confidence picks over volume
- Track all predictions for performance analysis
